from datetime import date, datetime

import pandas as pd
import streamlit as st

import db
from styling import inject_global_css, page_header

db.init_db()
inject_global_css()

page_header("Outreach List", "Every brand's stage and basic info, in one filterable, sortable list.")

def _to_date(value):
    if value in (None, "", "None") or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _to_iso(value):
    if value in (None, "",) or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)


def _saved_now():
    st.session_state["last_saved"] = datetime.now().strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Summary panel
# ---------------------------------------------------------------------------

df = db.fetch_all()
summary = db.compute_summary(df)

cols = st.columns(4)
cols[0].metric("Total emails", summary["total"])
cols[1].metric("Replied", summary["replied"])
cols[2].metric("No reply", summary["no_reply"])
rate = summary["reply_rate"]
cols[3].metric("Reply rate", f"{rate:.0%}" if rate is not None else "—")

if summary["date_min"] and summary["date_max"]:
    st.caption(f"Date range: {summary['date_min']} → {summary['date_max']}")

if summary["warnings"]:
    with st.expander(f"Data quality notes ({len(summary['warnings'])})"):
        for w in summary["warnings"]:
            st.caption(w)

top_left, top_right = st.columns([3, 1])
with top_left:
    if "last_saved" in st.session_state:
        st.caption(f"Saved at {st.session_state['last_saved']}")
with top_right:
    st.download_button(
        "Export to CSV",
        data=db.export_csv_bytes(df),
        file_name=f"mfbc_outreach_export_{date.today().isoformat()}.csv",
        mime="text/csv",
        width='stretch',
    )

active_batch = db.latest_active_batch_id()
if active_batch:
    if st.button("Undo last import", help="Removes every row from the most recent import."):
        removed = db.undo_import(active_batch)
        _saved_now()
        st.success(f"Removed {removed} row(s) from the last import.")
        st.rerun()

st.divider()

tab_all, tab_new, tab_comm, tab_future, tab_attending, tab_archived, tab_add, tab_import = st.tabs(
    [
        "All brands",
        "Brand ideas",
        "In communication",
        "Future participation",
        "Attending",
        "Archived",
        "Add one email",
        "Import CSV / Excel",
    ]
)

PIPELINE_VIEW_COLUMNS = [
    "company", "sender", "contact_name", "stage", "contact_role", "ask_type",
    "date_sent", "outcome", "notes",
]

STAGE_LABEL_OPTIONS = [db.STAGE_LABELS[s] for s in db.STAGES]
STAGE_LABEL_TO_KEY = {v: k for k, v in db.STAGE_LABELS.items()}


def _brand_table(stage_df, key_prefix):
    """Read-only, at-a-glance grid for a stage. Auto-sized to its row count
    (no internal scrollbar) — click a column header to sort it. Each row's
    clock icon opens that one brand's write-up on Brand History."""
    view_df = stage_df[PIPELINE_VIEW_COLUMNS].copy()
    view_df.insert(0, "history", "/history?brand_id=" + stage_df["id"].astype(int).astype(str))
    view_df["date_sent"] = view_df["date_sent"].apply(_to_date)
    view_df["stage"] = view_df["stage"].map(db.STAGE_LABELS)

    st.dataframe(
        view_df,
        key=f"{key_prefix}_brand_table",
        hide_index=True,
        width='stretch',
        height=40 + 35 * max(len(view_df), 1),
        column_config={
            "history": st.column_config.LinkColumn(
                " ", display_text="🕒", width="small", help="Open this brand's write-up on Brand History",
            ),
            "date_sent": st.column_config.DateColumn("Date sent"),
        },
    )


EDIT_COLUMN_CONFIG = {
    "id": st.column_config.NumberColumn("ID"),
    "company": st.column_config.TextColumn("Company", required=True),
    "contact_name": st.column_config.TextColumn("Contact name"),
    "contact_role": st.column_config.TextColumn("Contact role"),
    "ask_type": st.column_config.SelectboxColumn("Ask type", options=db.ASK_TYPES),
    "date_sent": st.column_config.DateColumn("Date sent"),
    "sender": st.column_config.TextColumn("Sender"),
    "is_follow_up": st.column_config.CheckboxColumn("Follow-up?"),
    "has_uw_mfbc_connection": st.column_config.CheckboxColumn("UW/MFBC connection?"),
    "has_prior_relationship": st.column_config.CheckboxColumn("Prior relationship?"),
    "email_text": st.column_config.TextColumn("Email text"),
    "notes": st.column_config.TextColumn("Notes"),
    "outcome": st.column_config.SelectboxColumn("Outcome", options=db.OUTCOMES),
    "reply_date": st.column_config.DateColumn("Reply date"),
    "stage": st.column_config.SelectboxColumn("Stage", options=db.STAGES, required=True),
}


def _inline_stage_editor(df, stage, key_prefix):
    """A spreadsheet-style editor scoped to one stage's rows, so editing a
    brand doesn't require leaving the tab it's already shown in."""
    editor_key = f"{key_prefix}_inline_editor"
    delete_key = f"{key_prefix}_pending_deletes"

    stage_df = df[df["stage"] == stage].copy()
    display_df = stage_df.copy()
    display_df["date_sent"] = display_df["date_sent"].apply(_to_date)
    display_df["reply_date"] = display_df["reply_date"].apply(_to_date)
    display_df = display_df.drop(columns=["created_at", "updated_at"])

    pending_deletes = st.session_state.get(delete_key)

    if pending_deletes:
        pending_rows = display_df[display_df["id"].isin(pending_deletes)]
        st.warning(
            f"You removed {len(pending_deletes)} row(s): "
            + ", ".join(pending_rows["company"].fillna("(no company)").tolist())
        )
        c1, c2 = st.columns(2)
        if c1.button("Confirm delete", type="primary", key=f"{key_prefix}_confirm_delete"):
            db.delete_records(pending_deletes)
            _saved_now()
            del st.session_state[delete_key]
            if editor_key in st.session_state:
                del st.session_state[editor_key]
            st.rerun()
        if c2.button("Keep row(s) (undo)", key=f"{key_prefix}_undo_delete"):
            del st.session_state[delete_key]
            if editor_key in st.session_state:
                del st.session_state[editor_key]
            st.rerun()
        return

    st.caption("Edit cells directly, or add a new row at the bottom. Changes save automatically.")
    st.data_editor(
        display_df,
        key=editor_key,
        num_rows="dynamic",
        hide_index=True,
        width='stretch',
        disabled=["id", "ai_chance_label", "ai_chance_reasoning", "ai_relied_on"],
        column_config=EDIT_COLUMN_CONFIG,
    )

    state = st.session_state.get(editor_key, {})
    edited_rows = state.get("edited_rows", {})
    added_rows = state.get("added_rows", [])
    deleted_rows = state.get("deleted_rows", [])

    if deleted_rows:
        ids = [int(display_df.iloc[pos]["id"]) for pos in deleted_rows]
        st.session_state[delete_key] = ids
        st.rerun()

    changed = False

    for pos, changes in edited_rows.items():
        row_id = int(display_df.iloc[int(pos)]["id"])
        base = display_df.iloc[int(pos)].to_dict()
        base.update(changes)
        record = {c: base.get(c) for c in db.EDITABLE_COLUMNS}
        record["date_sent"] = _to_iso(record.get("date_sent"))
        record["reply_date"] = _to_iso(record.get("reply_date"))
        for flag in ("is_follow_up", "has_uw_mfbc_connection", "has_prior_relationship"):
            record[flag] = int(bool(record.get(flag)))
        db.update_record(row_id, record)
        changed = True

    for new_row in added_rows:
        if not new_row.get("company"):
            continue
        record = {c: new_row.get(c) for c in db.EDITABLE_COLUMNS}
        record["date_sent"] = _to_iso(record.get("date_sent"))
        record["reply_date"] = _to_iso(record.get("reply_date"))
        for flag in ("is_follow_up", "has_uw_mfbc_connection", "has_prior_relationship"):
            record[flag] = int(bool(record.get(flag)))
        record.setdefault("ask_type", "other")
        record.setdefault("outcome", "no_reply")
        record["stage"] = new_row.get("stage") or stage
        db.insert_record(record)
        changed = True

    if changed:
        _saved_now()
        del st.session_state[editor_key]
        st.rerun()


def _edit_toggle(df, stage, key_prefix):
    """Renders the pencil button; returns True while that stage's inline
    editor is open (so the caller can hide its normal read-only view)."""
    editing_key = f"{key_prefix}_editing"
    editing = st.session_state.get(editing_key, False)
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("Edit" if not editing else "Done editing", key=f"{key_prefix}_edit_toggle"):
            st.session_state[editing_key] = not editing
            st.rerun()
    with c2:
        st.caption(
            "Click a row's clock icon for that brand's full write-up, response, or "
            "follow-up drafting on Brand History (top menu)."
            if not editing
            else "Change stage, company, or anything else here — it saves automatically."
        )
    if editing:
        _inline_stage_editor(df, stage, key_prefix)
    return editing


# ---------------------------------------------------------------------------
# Pipeline stage tabs
# ---------------------------------------------------------------------------

with tab_all:
    st.caption(
        f"{len(df)} brand(s)/people total. Click a column header to sort, or a row's clock "
        "icon for that brand's full write-up on Brand History (top menu)."
    )
    if df.empty:
        st.info("Nothing logged yet.")
    else:
        _brand_table(df, "all")

with tab_new:
    new_df = df[df["stage"] == "new"].copy()
    st.caption(
        f"{len(new_df)} brand(s)/people not yet contacted. Pick one to draft an outreach "
        "email and see a rough reply-chance estimate before you send."
    )
    editing = _edit_toggle(df, "new", "new")
    if not editing:
        if new_df.empty:
            st.info("Nothing in Brand ideas right now.")
        else:
            _brand_table(new_df, "new")
            name_counts = new_df["company"].value_counts()
            options = {
                (
                    f"{row.company} — {row.sender}" if name_counts.get(row.company, 0) > 1 and row.sender
                    else row.company
                ): row.id
                for row in new_df.itertuples()
            }
            choice = st.selectbox("Choose a brand", list(options.keys()), key="new_brand_choice")
            if choice:
                target_id = options[choice]
                target = new_df[new_df["id"] == target_id].iloc[0].to_dict()
                chance = db.estimate_reply_chance(target, df)
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("Rough reply chance", chance["label"])
                with c2:
                    st.caption(
                        "A quick estimate from connection/relationship signals and the "
                        "club's reply history so far"
                        + (
                            f" ({chance['base_replied']}/{chance['base_n']} replied club-wide)."
                            if chance["base_n"]
                            else " (no outcomes logged yet)."
                        )
                    )
                    st.caption(" · ".join(chance["reasons"]))
                if st.button("Draft email for this brand", type="primary"):
                    st.session_state["draft_target_id"] = int(target_id)
                    st.switch_page("views/2_Draft_Email.py")

with tab_comm:
    comm_df = df[df["stage"] == "in_communication"].copy()
    st.caption(f"{len(comm_df)} brand(s) sent and waiting on / discussing a response.")
    editing = _edit_toggle(df, "in_communication", "comm")
    if not editing:
        if comm_df.empty:
            st.info("Nothing in In communication right now.")
        else:
            _brand_table(comm_df, "comm")

with tab_future:
    future_df = df[df["stage"] == "future_participation"].copy()
    st.caption(
        f"{len(future_df)} brand(s) that said yes in some form, but for a later semester or "
        "event rather than right now — follow up with them when the timing's right."
    )
    editing = _edit_toggle(df, "future_participation", "future")
    if not editing:
        if future_df.empty:
            st.info("Nothing in Future participation right now.")
        else:
            _brand_table(future_df, "future")

with tab_attending:
    attending_df = df[df["stage"] == "attending"].copy()
    st.caption(f"{len(attending_df)} brand(s)/people confirmed or already part of a past convention.")
    editing = _edit_toggle(df, "attending", "attending")
    if not editing:
        if attending_df.empty:
            st.info("Nothing confirmed as attending yet.")
        else:
            _brand_table(attending_df, "attending")

with tab_archived:
    archived_df = df[df["stage"] == "archived"].copy()
    st.caption(f"{len(archived_df)} brand(s) closed out (declined or no longer pursuing).")
    editing = _edit_toggle(df, "archived", "archived")
    if not editing:
        if archived_df.empty:
            st.info("Nothing archived right now.")
        else:
            _brand_table(archived_df, "archived")

# ---------------------------------------------------------------------------
# Tab: Add one email
# ---------------------------------------------------------------------------

with tab_add:
    with st.form("add_email_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            company = st.text_input("Company *")
            contact_name = st.text_input("Contact name")
            contact_role = st.text_input("Contact role")
            ask_type = st.selectbox("Type of ask", db.ASK_TYPES, format_func=lambda k: db.ASK_TYPE_LABELS[k])
            date_sent = st.date_input("Date sent", value=None)
            sender = st.text_input("Sender (MFBC member who sent it)")
        with c2:
            is_follow_up = st.checkbox("This is a follow-up")
            has_uw_mfbc_connection = st.checkbox("UW or MFBC connection")
            has_prior_relationship = st.checkbox("Prior relationship with this company/contact")
            outcome = st.selectbox("Outcome", db.OUTCOMES, format_func=lambda k: db.OUTCOME_LABELS[k])
            reply_date = st.date_input("Reply date (if any)", value=None)
            stage_choice = st.selectbox(
                "Pipeline stage", ["(auto)"] + db.STAGES,
                format_func=lambda k: k if k == "(auto)" else db.STAGE_LABELS[k],
            )
        email_text = st.text_area("Email text (optional)")
        notes = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Add email", type="primary")
        if submitted:
            if not company.strip():
                st.error("Company is required.")
            else:
                record = {
                    "company": company.strip(),
                    "contact_name": contact_name.strip() or None,
                    "contact_role": contact_role.strip() or None,
                    "ask_type": ask_type,
                    "date_sent": _to_iso(date_sent),
                    "sender": sender.strip() or None,
                    "is_follow_up": int(is_follow_up),
                    "has_uw_mfbc_connection": int(has_uw_mfbc_connection),
                    "has_prior_relationship": int(has_prior_relationship),
                    "email_text": email_text.strip() or None,
                    "notes": notes.strip() or None,
                    "outcome": outcome,
                    "reply_date": _to_iso(reply_date),
                    "stage": None if stage_choice == "(auto)" else stage_choice,
                }
                issues = db.validate_record(record)
                db.insert_record(record)
                _saved_now()
                if issues:
                    st.warning("Saved, but flagged: " + "; ".join(issues))
                else:
                    st.success(f"Added outreach to {record['company']}.")
                st.rerun()

# ---------------------------------------------------------------------------
# Tab: CSV / Excel import
# ---------------------------------------------------------------------------

with tab_import:
    st.caption(
        "Upload a spreadsheet, match its columns to the fields below, preview what will "
        "be imported, then confirm. Exact duplicates (same company, contact, date sent, "
        "and ask type as an existing record) are skipped automatically."
    )

    uploaded = st.file_uploader("CSV or Excel file", type=["csv", "xlsx", "xls"])

    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                raw_df = pd.read_csv(uploaded)
            else:
                raw_df = pd.read_excel(uploaded)
        except Exception as exc:
            st.error(f"Couldn't read that file: {exc}")
            raw_df = None

        if raw_df is not None and not raw_df.empty:
            st.write(f"Found **{len(raw_df)}** row(s) with columns: {', '.join(raw_df.columns.astype(str))}")

            st.markdown("**Match your columns to the app's fields**")
            file_columns = ["— none —"] + list(raw_df.columns.astype(str))
            mapping = {}
            map_cols = st.columns(3)
            for i, field in enumerate(db.EDITABLE_COLUMNS):
                with map_cols[i % 3]:
                    guess = field if field in raw_df.columns else "— none —"
                    mapping[field] = st.selectbox(
                        field, file_columns, index=file_columns.index(guess), key=f"map_{field}"
                    )

            records = []
            for _, row in raw_df.iterrows():
                record = {}
                for field, src_col in mapping.items():
                    if src_col == "— none —":
                        record[field] = None
                    else:
                        val = row[src_col]
                        record[field] = None if pd.isna(val) else val
                if record.get("date_sent"):
                    record["date_sent"] = _to_iso(_to_date(record["date_sent"]))
                if record.get("reply_date"):
                    record["reply_date"] = _to_iso(_to_date(record["reply_date"]))
                for flag in ("is_follow_up", "has_uw_mfbc_connection", "has_prior_relationship"):
                    record[flag] = int(bool(record.get(flag)))
                if record.get("ask_type"):
                    record["ask_type"] = str(record["ask_type"]).strip().lower()
                if record.get("outcome"):
                    record["outcome"] = str(record["outcome"]).strip().lower().replace(" ", "_")
                records.append(record)

            existing_keys = {db.dup_key(r) for r in df.to_dict("records")}
            preview_rows = []
            seen = set()
            for r in records:
                key = db.dup_key(r)
                issues = db.validate_record(r)
                is_dup = key in existing_keys or key in seen
                if is_dup:
                    issues = issues + ["duplicate — will be skipped"]
                else:
                    seen.add(key)
                preview_rows.append({**r, "_issues": "; ".join(issues) if issues else ""})

            preview_df = pd.DataFrame(preview_rows)
            will_import = sum(1 for r in preview_rows if "duplicate" not in r["_issues"])
            will_skip = len(preview_rows) - will_import
            st.markdown(f"**Preview:** {will_import} row(s) will be imported, {will_skip} skipped as duplicates.")
            st.dataframe(preview_df, width='stretch', height=300)

            if st.button("Import", type="primary"):
                result = db.bulk_import(records)
                _saved_now()
                st.success(
                    f"Imported {result['inserted']} row(s), skipped {result['skipped_duplicate']} duplicate(s)."
                )
                if result["row_issues"]:
                    with st.expander(f"{len(result['row_issues'])} row(s) flagged"):
                        for item in result["row_issues"]:
                            st.write(f"- {item['company']}: {', '.join(item['issues'])}")
                st.rerun()
