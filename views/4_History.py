from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import db
import drafting
from styling import inject_global_css, page_header

db.init_db()
inject_global_css()

page_header(
    "Brand History",
    "Each company's background and our outreach email history with them — research, "
    "messages, responses, and notes, in one place.",
)

SORT_OPTIONS = {
    "Stage": ("stage", True),
    "Date sent (newest first)": ("_date", False),
    "Date sent (oldest first)": ("_date", True),
    "Company (A-Z)": ("company", True),
    "Company (Z-A)": ("company", False),
    "Outcome": ("outcome", True),
}

# Business-meaningful order for "Sort by: Stage" — not alphabetical. In
# communication and Attending lead since those are the most active/relevant
# brands to check first; anything outside this list sorts after.
STAGE_SORT_ORDER = ["in_communication", "attending", "future_participation", "new", "archived"]


def _to_date(value):
    if value in (None, "", "None") or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _render_brand_detail(row):
    """Everything known about one brand: stage/outcome, the saved message, the AI
    research behind it, notes, their response, and follow-up drafting."""
    st.subheader(row["company"] or "(no company name)")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stage", db.STAGE_LABELS.get(row["stage"], row["stage"]))
    c2.metric("Date sent", row["date_sent"] or "—")
    c3.metric("Outcome", db.OUTCOME_LABELS.get(row["outcome"], row["outcome"] or "—"))
    c4.metric("Sender", row["sender"] or "—")

    if row["contact_name"] or row["contact_role"]:
        st.caption(f"Contact: {row['contact_name'] or '—'} ({row['contact_role'] or 'role unknown'})")
    st.caption(f"Type of ask: {db.ASK_TYPE_LABELS.get(row['ask_type'], row['ask_type'] or '—')}")

    st.subheader("Saved message")
    if row["email_text"]:
        st.text_area(
            "Saved message", value=row["email_text"], height=280,
            key=f"history_email_{row['id']}", label_visibility="collapsed", disabled=True,
        )
    else:
        st.caption("No message drafted or sent for this one yet.")

    st.subheader("AI research behind it")
    if row.get("ai_chance_label") or row.get("ai_chance_reasoning") or row.get("ai_relied_on"):
        if row.get("ai_chance_label"):
            rc1, rc2 = st.columns([1, 3])
            rc1.metric("Researched reply chance", row["ai_chance_label"])
            rc2.caption(row.get("ai_chance_reasoning") or "")
        elif row.get("ai_chance_reasoning"):
            st.caption(row["ai_chance_reasoning"])
        if row.get("ai_relied_on"):
            st.write(row["ai_relied_on"])
    else:
        st.caption(
            "No AI research saved for this one — it was drafted with the free template, "
            "hasn't been drafted yet, or was saved before this history feature existed."
        )

    if row["notes"]:
        st.subheader("Notes on this brand")
        st.write(row["notes"])

    st.divider()
    show_response_key = f"show_response_{row['id']}"
    rc1, rc2 = st.columns(2)
    with rc1:
        if st.button("Input their response", key=f"toggle_response_{row['id']}"):
            st.session_state[show_response_key] = not st.session_state.get(show_response_key, False)
    with rc2:
        has_response = bool((row.get("response_text") or "").strip())
        gen_caption = (
            "drafts a response to what they said" if has_response
            else "drafts a reminder/follow-up (no reply on file yet)"
        )
        if st.button("Generate another email", type="primary", key=f"generate_email_{row['id']}"):
            if not drafting.api_key_available():
                st.error(
                    "ANTHROPIC_API_KEY isn't set, so this can't call the Claude API. Set it "
                    "as an environment variable to use it."
                )
            else:
                with st.spinner("Drafting..."):
                    try:
                        if has_response:
                            result = drafting.draft_followup(row.to_dict(), row["response_text"])
                        else:
                            result = drafting.draft_reminder(row.to_dict())
                        st.session_state[f"followup_draft_{row['id']}"] = result["draft"]
                    except Exception as exc:
                        st.error(f"Couldn't draft an email: {exc}")
        st.caption(f"Claude {gen_caption}, using the email already sent and what MFBC knows.")

    if st.session_state.get(show_response_key):
        st.subheader("Their response")
        st.caption(
            "Paste what they wrote back — saving this is what lets Generate draft a reply "
            "instead of a reminder."
        )

        response_value = st.text_area(
            "Their response", value=row.get("response_text") or "",
            key=f"response_text_{row['id']}", height=150, label_visibility="collapsed",
        )
        reply_date_value = st.date_input(
            "Date they replied", value=_to_date(row.get("reply_date")),
            key=f"reply_date_{row['id']}",
        )
        if st.button("Save response", key=f"save_response_{row['id']}"):
            record = {c: row.get(c) for c in db.EDITABLE_COLUMNS}
            record["response_text"] = response_value.strip() or None
            record["reply_date"] = reply_date_value.isoformat() if reply_date_value else None
            db.update_record(int(row["id"]), record)
            st.success("Saved.")
            st.rerun()

    draft_key = f"followup_draft_{row['id']}"
    if draft_key in st.session_state:
        st.subheader("Drafted email")
        edited = st.text_area(
            "Drafted email", value=st.session_state[draft_key], height=240,
            key=f"followup_box_{row['id']}", label_visibility="collapsed",
        )
        st.caption("Check every claim before sending — this tool never sends email on its own.")
        fc1, fc2 = st.columns(2)
        with fc1:
            if st.button("Save as this brand's draft", key=f"save_followup_draft_{row['id']}"):
                record = {c: row.get(c) for c in db.EDITABLE_COLUMNS}
                record["email_text"] = edited
                record["is_follow_up"] = True
                db.update_record(int(row["id"]), record)
                st.success("Saved.")
                st.rerun()
        with fc2:
            followup_sent_date = st.date_input(
                "Date sent", value=date.today(), key=f"followup_sent_date_{row['id']}",
            )
            if st.button("Mark follow-up as sent", key=f"mark_followup_sent_{row['id']}"):
                record = {c: row.get(c) for c in db.EDITABLE_COLUMNS}
                record["email_text"] = edited
                record["is_follow_up"] = True
                record["date_sent"] = followup_sent_date.isoformat()
                db.update_record(int(row["id"]), record)
                st.success(f"Marked as sent on {followup_sent_date.isoformat()}.")
                st.rerun()


@st.dialog("Brand details", width="large")
def _brand_dialog(row):
    if st.button("← Back to list", key=f"close_dialog_{row['id']}"):
        st.session_state["history_scroll_to_id"] = int(row["id"])
        st.rerun()
    _render_brand_detail(row)
    st.divider()
    if st.button("← Back to list", key=f"close_dialog_bottom_{row['id']}"):
        st.session_state["history_scroll_to_id"] = int(row["id"])
        st.rerun()


df = db.fetch_all()

deep_link_id = st.query_params.get("brand_id")
if deep_link_id is not None:
    st.query_params.pop("brand_id", None)

if df.empty:
    st.info("Nothing logged yet — start on Outreach List.")
else:
    if deep_link_id is not None:
        match = df[df["id"] == int(deep_link_id)] if deep_link_id.isdigit() else df.iloc[0:0]
        if not match.empty:
            _brand_dialog(match.iloc[0])

    st.subheader("Brand Specifics")
    st.caption(
        f"{len(df)} brand(s)/people total. Click a company to open its full write-up in a "
        "pop-up — this always reflects what's currently in Outreach List."
    )

    c1, c2, c3 = st.columns([2, 1, 0.6])
    with c1:
        search = st.text_input("Search by company name", key="history_search", placeholder="e.g. Shopbop")
    with c2:
        sort_choice = st.selectbox(
            "Sort by", list(SORT_OPTIONS.keys()), index=0, key="history_sort_by",
        )
    with c3:
        st.write("")
        st.write("")
        if st.button("Clear search", disabled=not search.strip()):
            st.session_state["history_search"] = ""
            st.rerun()
    sort_col, ascending = SORT_OPTIONS[sort_choice]

    list_df = df.copy()
    sent_key = pd.to_datetime(list_df["date_sent"], errors="coerce")
    logged_key = pd.to_datetime(list_df["created_at"], errors="coerce")
    list_df["_date"] = sent_key.fillna(logged_key)

    if search.strip():
        list_df = list_df[list_df["company"].str.contains(search.strip(), case=False, na=False)]

    if sort_col == "company":
        list_df = list_df.sort_values(
            "company", ascending=ascending, na_position="last",
            key=lambda s: s.astype(str).str.lower(),
        )
    elif sort_col == "stage":
        list_df = list_df.sort_values(
            "stage", ascending=ascending, na_position="last",
            key=lambda s: s.map(lambda v: STAGE_SORT_ORDER.index(v) if v in STAGE_SORT_ORDER else len(STAGE_SORT_ORDER)),
        )
    else:
        list_df = list_df.sort_values(sort_col, ascending=ascending, na_position="last")

    st.divider()
    if list_df.empty:
        st.caption("No brands match that search.")
    else:
        for item in list_df.itertuples():
            st.markdown(f'<div id="brand-anchor-{item.id}"></div>', unsafe_allow_html=True)
            if st.button(item.company or "(no company name)", key=f"brand_specifics_{item.id}"):
                st.session_state["history_selected_id"] = int(item.id)
                _brand_dialog(df[df["id"] == item.id].iloc[0])
            bits = [str(db.STAGE_LABELS.get(item.stage, item.stage))]
            if pd.notna(item.sender) and item.sender:
                bits.append(f"Sender: {item.sender}")
            if pd.notna(item.date_sent) and item.date_sent:
                bits.append(f"Sent {item.date_sent}")
            if pd.notna(item.outcome) and item.outcome:
                bits.append(str(db.OUTCOME_LABELS.get(item.outcome, item.outcome)))
            st.caption(" · ".join(bits))
            st.divider()

    scroll_to_id = st.session_state.pop("history_scroll_to_id", None)
    if scroll_to_id is not None:
        components.html(
            f"""
            <script>
            setTimeout(function() {{
                var doc = window.parent.document;
                var el = doc.getElementById('brand-anchor-{scroll_to_id}');
                if (el) {{ el.scrollIntoView({{behavior: 'instant', block: 'start'}}); }}
            }}, 150);
            </script>
            """,
            height=0,
        )
