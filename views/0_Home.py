import streamlit as st

import db
from styling import inject_global_css, page_header

db.init_db()
inject_global_css()

page_header("MFBC Outreach Assistant", "Draft outreach, estimate reply chances, track the pipeline.")

st.info(
    "**Start with Outreach List** (top menu) to enter or import past and ongoing "
    "outreach — drafting and the reply-chance estimate are built on top of that data."
)

df = db.fetch_all()
summary = db.compute_summary(df)
cols = st.columns(4)
cols[0].metric("Total emails logged", summary["total"])
cols[1].metric("Replied", summary["replied"])
cols[2].metric("No reply", summary["no_reply"])
rate = summary["reply_rate"]
cols[3].metric("Reply rate", f"{rate:.0%}" if rate is not None else "—")

st.divider()
st.subheader("Follow-ups")

in_comm = df[df["stage"] == "in_communication"].copy()
needs_follow_up = in_comm[in_comm["outcome"].isin(["replied", "meeting_booked"])]
awaiting_reply = in_comm[in_comm["outcome"].isna() | (in_comm["outcome"] == "no_reply")]

if needs_follow_up.empty and awaiting_reply.empty:
    st.caption("Nothing in In communication right now — no follow-ups today.")
else:
    lines = []
    for row in needs_follow_up.itertuples():
        who = f" — {row.sender}" if row.sender else ""
        lines.append(f"- **Follow up with:** {row.company}{who}")
    for row in awaiting_reply.itertuples():
        who = f" — {row.sender}" if row.sender else ""
        lines.append(f"- **Awaiting response from:** {row.company}{who}")
    st.markdown("\n".join(lines))

st.divider()
st.subheader("MFBC Research Notes")
st.caption(
    "Facts gathered from MFBC's own website and Instagram. This is what Claude reads as "
    "background when it researches and drafts, so keep it accurate — edits here change "
    "future AI drafts, not just this page."
)

notes_editing = st.session_state.get("club_notes_editing", False)
if st.button("Edit" if not notes_editing else "Done editing", key="club_notes_edit_toggle"):
    st.session_state["club_notes_editing"] = not notes_editing
    st.rerun()

club_notes = db.fetch_club_notes()
if not club_notes:
    st.caption("No notes recorded yet.")
elif notes_editing:
    for note in club_notes:
        c1, c2 = st.columns([5, 1])
        c1.write(f"- {note['text']}")
        if c2.button("Remove", key=f"remove_note_{note['id']}"):
            db.delete_club_note(note["id"])
            st.rerun()
else:
    st.markdown("\n".join(f"- {note['text']}" for note in club_notes))

if notes_editing:
    add_key = f"new_club_note_text_{st.session_state.get('club_note_add_version', 0)}"
    new_note_text = st.text_area("Add a new bullet", key=add_key)
    if st.button("Add bullet", type="primary"):
        if new_note_text.strip():
            db.add_club_note(new_note_text)
            st.session_state["club_note_add_version"] = st.session_state.get("club_note_add_version", 0) + 1
            st.rerun()
