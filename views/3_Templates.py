from datetime import datetime

import streamlit as st

import db
from styling import inject_global_css, page_header

db.init_db()
inject_global_css()

page_header("Email Templates", "Powers the free, no-cost drafting mode — no API calls, nothing spent.")
st.caption(
    "Use placeholders like {contact_name}, {company}, {sender}, {ask_type_label}, and "
    "{reason} (auto-filled from the snippets below based on the brand's info)."
)


def _saved_now():
    st.session_state["last_saved_templates"] = datetime.now().strftime("%H:%M:%S")


if "last_saved_templates" in st.session_state:
    st.caption(f"Saved at {st.session_state['last_saved_templates']}")

st.divider()
st.subheader("Templates")

templates = db.fetch_templates()
for row in templates.itertuples():
    with st.expander(row.name, expanded=len(templates) == 1):
        with st.form(f"template_{row.id}"):
            name = st.text_input("Name", value=row.name, key=f"name_{row.id}")
            body = st.text_area("Body", value=row.body, height=220, key=f"body_{row.id}")
            c1, c2 = st.columns(2)
            if c1.form_submit_button("Save", type="primary"):
                db.save_template(row.id, name.strip(), body)
                _saved_now()
                st.rerun()
            if c2.form_submit_button("Delete this template"):
                db.delete_template(row.id)
                _saved_now()
                st.rerun()

with st.expander("Add a new template"):
    with st.form("new_template", clear_on_submit=True):
        name = st.text_input("Name")
        body = st.text_area(
            "Body",
            value="Hi {contact_name},\n\n{reason}\n\nBest,\n{sender}\nMFBC",
            height=180,
        )
        if st.form_submit_button("Add template", type="primary"):
            if name.strip():
                db.save_template(None, name.strip(), body)
                _saved_now()
                st.rerun()
            else:
                st.error("Give the template a name.")

st.divider()
st.subheader("Reason snippets")
st.caption(
    "Auto-selected based on a brand's info and dropped into {reason}. If more than one "
    "applies (e.g. sponsorship ask + UW connection), they're combined."
)

snippets = db.fetch_snippets()
for row in snippets.itertuples():
    with st.form(f"snippet_{row.condition_key}"):
        st.caption(row.label)
        text = st.text_area("Text", value=row.text, key=f"snippet_text_{row.condition_key}", height=70)
        if st.form_submit_button("Save"):
            db.save_snippet(row.condition_key, text)
            _saved_now()
            st.rerun()
