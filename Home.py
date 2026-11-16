import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MFBC Outreach Assistant", layout="wide")

app_password = os.environ.get("APP_PASSWORD")
if app_password:
    if not st.session_state.get("authed"):
        st.title("MFBC Outreach Assistant")
        entered = st.text_input("Password", type="password")
        if entered:
            if entered == app_password:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
        st.stop()

pages = [
    st.Page("views/0_Home.py", title="Home", url_path="home", default=True),
    st.Page("views/1_Outreach_History.py", title="Outreach List", url_path="outreach-history"),
    st.Page("views/2_Draft_Email.py", title="Draft Email", url_path="draft-email"),
    st.Page("views/3_Templates.py", title="Templates", url_path="templates"),
    st.Page("views/4_History.py", title="Brand History", url_path="history"),
]

nav = st.navigation(pages, position="top")
nav.run()
