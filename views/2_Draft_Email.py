from datetime import date, datetime

import streamlit as st

import db
import drafting
from styling import inject_global_css, page_header

db.init_db()
inject_global_css()

page_header("Draft Outreach Email", "Drafts only — a member always reviews and sends it themselves.")

df = db.fetch_all()
new_df = df[df["stage"] == "new"].copy()

target_id = st.session_state.get("draft_target_id")
target = None
if target_id is not None:
    match = df[df["id"] == target_id]
    if not match.empty:
        target = match.iloc[0].to_dict()

st.subheader("1. Who is this for?")
source_mode = st.radio(
    "Brand source",
    ["Pick from New brand", "Enter a brand not logged yet"],
    horizontal=True,
    index=0 if target is not None else (0 if not new_df.empty else 1),
)

if source_mode == "Pick from New brand":
    if new_df.empty:
        st.info("Nothing in New brand to pick from — switch to entering one manually.")
        brand_info = None
    else:
        default_idx = 0
        name_counts = new_df["company"].value_counts()
        options = {
            (
                f"{row.company} — {row.sender}" if name_counts.get(row.company, 0) > 1 and row.sender
                else row.company
            ): row.id
            for row in new_df.itertuples()
        }
        if target is not None:
            for i, (label, rid) in enumerate(options.items()):
                if rid == target_id:
                    default_idx = i
        choice = st.selectbox("Brand", list(options.keys()), index=default_idx)
        row_id = options[choice]
        brand_info = df[df["id"] == row_id].iloc[0].to_dict()
else:
    c1, c2 = st.columns(2)
    with c1:
        company = st.text_input("Company *")
        contact_name = st.text_input("Contact name")
        contact_role = st.text_input("Contact role")
    with c2:
        ask_type = st.selectbox("Type of ask", db.ASK_TYPES, format_func=lambda k: db.ASK_TYPE_LABELS[k])
        has_uw_mfbc_connection = st.checkbox("UW or MFBC connection")
        has_prior_relationship = st.checkbox("Prior relationship")
    notes = st.text_area("Notes about this brand")
    sender = st.text_input("Sender (your name)")
    brand_info = {
        "id": None,
        "company": company.strip(),
        "contact_name": contact_name.strip() or None,
        "contact_role": contact_role.strip() or None,
        "ask_type": ask_type,
        "has_uw_mfbc_connection": has_uw_mfbc_connection,
        "has_prior_relationship": has_prior_relationship,
        "is_follow_up": False,
        "notes": notes.strip() or None,
        "sender": sender.strip() or None,
    } if company.strip() else None

    # Once this manually-entered brand has been saved once, reuse that same
    # row for later saves in this session instead of creating a duplicate
    # every time "Save draft" / "Mark as sent" is clicked.
    if brand_info and st.session_state.get("manual_entry_saved_company") == brand_info["company"]:
        brand_info["id"] = st.session_state.get("manual_entry_saved_id")
        for field in ("ai_chance_label", "ai_chance_reasoning", "ai_relied_on"):
            brand_info[field] = st.session_state.get(f"manual_entry_saved_{field}")

if brand_info:
    if source_mode == "Pick from New brand":
        chance = db.estimate_reply_chance(brand_info, df)
        c1, c2 = st.columns([1, 3])
        c1.metric("Rough reply chance", chance["label"])
        c2.caption(
            f"A quick estimate from connection/relationship signals and the club's reply "
            f"history so far ({chance['base_n']} logged outcome(s)). " + " · ".join(chance["reasons"])
        )
    else:
        st.caption(
            "No reply-chance estimate yet for a brand that isn't logged — switch to "
            "AI-generated drafting mode below and Claude will research this company's size "
            "and public profile to give a grounded estimate, instead of guessing from "
            "connection checkboxes."
        )

    st.subheader("2. Draft it")
    draft_mode = st.radio(
        "Drafting mode",
        ["Free template (no cost)", "AI-generated (Claude API — costs a small amount)"],
        horizontal=True,
    )

    edited_draft = None
    relied_on = None
    result = None

    if draft_mode == "Free template (no cost)":
        templates = db.fetch_templates()
        if templates.empty:
            st.warning("No templates yet — add one on the Templates page.")
        else:
            t_options = {row.name: row for row in templates.itertuples()}
            t_choice = st.selectbox("Template", list(t_options.keys()))
            template_row = t_options[t_choice]
            st.caption(
                "No API call, nothing spent. Edit the [Templates](/Templates) page to "
                "change the wording, then click below to (re)fill it with this brand's info."
            )
            if st.button("Fill in template"):
                rendered = db.render_template(template_row.body, brand_info)
                st.session_state["free_draft_text"] = rendered
                st.session_state["free_draft_version"] = st.session_state.get("free_draft_version", 0) + 1

            if "free_draft_text" in st.session_state:
                edited_draft = st.text_area(
                    "Draft email", value=st.session_state["free_draft_text"], height=280,
                    key=f"free_draft_box_{st.session_state.get('free_draft_version', 0)}",
                )
    else:
        if not drafting.api_key_available():
            st.error(
                "ANTHROPIC_API_KEY isn't set, so this mode can't call the Claude API. "
                "Set it as an environment variable (never hard-coded) to use it:\n\n"
                "`export ANTHROPIC_API_KEY=sk-ant-...`"
            )
        else:
            st.caption(
                "Claude will search the web for real public info about this company, weigh it "
                "against MFBC's own outreach history, and draft an email explaining specifically "
                "why they'd want to be part of MFBC — not a generic template. This can take a "
                "minute or so since it's doing real research; it won't stop early with a "
                "half-finished draft."
            )
            extra_info = st.text_area(
                "Anything else you already know about them? (optional — Claude researches the "
                "rest itself)",
                key="extra_public_info",
            )
            if st.button("Research & draft with AI", type="primary"):
                with st.spinner("Researching the company and drafting — this can take a minute..."):
                    try:
                        result = drafting.research_and_draft(brand_info, df, extra_info)
                        st.session_state["ai_draft_result"] = result
                        st.session_state["ai_draft_version"] = st.session_state.get("ai_draft_version", 0) + 1
                    except Exception as exc:
                        st.error(f"Couldn't generate a draft: {exc}")

            result = st.session_state.get("ai_draft_result")
            if result:
                if result.get("chance_label"):
                    c1, c2 = st.columns([1, 3])
                    c1.metric("Researched reply chance", result["chance_label"])
                    c2.caption(result["chance_reasoning"])
                elif result.get("chance_reasoning"):
                    st.caption(result["chance_reasoning"])

                edited_draft = st.text_area(
                    "Draft email", value=result["draft"], height=280,
                    key=f"ai_draft_text_{st.session_state.get('ai_draft_version', 0)}",
                )
                relied_on = result["relied_on"]

    def _save_record(extra_fields=None):
        """Insert or update this brand's row, carrying the draft text and any
        AI research along with it. For a manually-entered brand, remembers
        the row it just created so later saves in this session update that
        same row instead of creating a duplicate every time."""
        record = {c: brand_info.get(c) for c in db.EDITABLE_COLUMNS}
        record["email_text"] = edited_draft
        if result:
            record["ai_chance_label"] = result.get("chance_label")
            record["ai_chance_reasoning"] = result.get("chance_reasoning") or None
            record["ai_relied_on"] = result.get("relied_on") or None
        else:
            record["ai_chance_label"] = brand_info.get("ai_chance_label")
            record["ai_chance_reasoning"] = brand_info.get("ai_chance_reasoning")
            record["ai_relied_on"] = brand_info.get("ai_relied_on")
        if extra_fields:
            record.update(extra_fields)

        if brand_info.get("id") is not None:
            db.update_record(int(brand_info["id"]), record)
            return int(brand_info["id"])

        record.setdefault("outcome", None)
        new_id = db.insert_record(record)
        st.session_state["manual_entry_saved_id"] = new_id
        st.session_state["manual_entry_saved_company"] = brand_info["company"]
        st.session_state["manual_entry_saved_ai_chance_label"] = record["ai_chance_label"]
        st.session_state["manual_entry_saved_ai_chance_reasoning"] = record["ai_chance_reasoning"]
        st.session_state["manual_entry_saved_ai_relied_on"] = record["ai_relied_on"]
        return new_id

    if edited_draft:
        if relied_on:
            with st.expander("What this draft relied on"):
                st.write(relied_on)
        st.caption(
            "Check every placeholder in brackets and every claim before sending — this "
            "tool never sends email on its own."
        )

        st.subheader("3. Save it")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save draft to this brand's record"):
                _save_record()
                st.success("Draft saved.")
                st.rerun()
        with c2:
            sent_date = st.date_input("Date actually sent", value=date.today())
            if st.button("Mark as sent"):
                _save_record({"date_sent": sent_date.isoformat(), "stage": "in_communication"})
                st.session_state.pop("ai_draft_result", None)
                st.session_state.pop("draft_target_id", None)
                st.success(f"Marked as sent on {sent_date.isoformat()} and moved to In communication.")
                st.switch_page("views/1_Outreach_History.py")
