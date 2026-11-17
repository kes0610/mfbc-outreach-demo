"""Shared branded styling for every page — an editorial, black-and-white-
photography-and-red-accent look pulled from a full read of MFBC's own
Instagram (bold circular wordmark, all-caps display headers, a confident
red used across their convention/sponsor graphics), instead of Streamlit's
generic defaults or a generic "cozy fall" palette."""

import streamlit as st

CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
h1, h2, h3, .mfbc-display {
    font-family: 'Fraunces', serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
    color: #1A1A1A !important;
}
h2, h3 {
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 1.1rem !important;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #FAF8F4 400px);
}
[data-testid="stSidebar"] {
    background-color: #EDEAE2;
    border-right: 1px solid #D8D3C6;
}
[data-testid="stSidebar"] a, [data-testid="stSidebar"] span {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.85rem;
    letter-spacing: 0.03em;
}

/* Branded header badge + wordmark */
.mfbc-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 4px;
}
.mfbc-badge {
    flex-shrink: 0;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: #1A1A1A;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 14px;
    letter-spacing: 0.02em;
    border: 3px solid #A61C33;
}
.mfbc-header-title {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 2rem;
    color: #1A1A1A;
    line-height: 1.1;
    margin: 0;
}
.mfbc-header-subtitle {
    font-family: 'Inter', sans-serif;
    color: #6B6B6B;
    font-size: 0.95rem;
    margin-top: 2px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E5E1D8;
    border-top: 3px solid #A61C33;
    border-radius: 4px;
    padding: 14px 16px 10px 16px;
}
[data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.04em;
    color: #6B6B6B;
}
[data-testid="stMetricValue"] {
    font-family: 'Fraunces', serif;
    color: #A61C33;
}

/* Buttons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: 2px;
    border: 1px solid #A61C33;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-size: 0.85rem;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background-color: #A61C33;
    border-color: #A61C33;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
    background-color: #7E1427;
    border-color: #7E1427;
}
.stButton > button:disabled, .stButton > button[kind="primary"]:disabled,
.stButton > button:disabled:hover, .stButton > button[kind="primary"]:disabled:hover {
    background-color: #EDEAE2;
    border-color: #D8D3C6;
    color: #6B6B6B;
}

/* Top navigation (st.navigation position="top") */
[data-testid="stHeader"] {
    background-color: #FFFFFF;
    border-bottom: 1px solid #D8D3C6;
}
[data-testid="stTopNavLink"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    font-size: 0.8rem !important;
    letter-spacing: 0.04em;
    color: #1A1A1A !important;
}
[data-testid="stTopNavLink"] span {
    color: inherit !important;
}
[data-testid="stTopNavLink"][aria-current="page"] {
    color: #A61C33 !important;
    border-bottom: 2px solid #A61C33;
}

/* Alerts — muted parchment callouts with a colored left rule, instead of
   Streamlit's bright default info/warning/success/error fills. */
[data-testid="stAlertContainer"] {
    background-color: #FAF8F4 !important;
    border-radius: 2px;
    border: 1px solid #E5E1D8;
}
[data-testid="stAlertContentInfo"],
[data-testid="stAlertContentWarning"],
[data-testid="stAlertContentSuccess"],
[data-testid="stAlertContentError"] {
    color: #1A1A1A !important;
    border-left: 3px solid #1A1A1A;
    padding-left: 12px;
}
[data-testid="stAlertContentWarning"],
[data-testid="stAlertContentError"] {
    border-left-color: #A61C33;
}

/* Streamlit shows a random whimsical icon (a runner, a cyclist, ...) in
   the toolbar while the app is running — nothing to do with this app's
   content. Hide it and overlay a plain branded spinner instead. */
[data-testid="stStatusWidgetRunningIcon"] {
    position: relative;
}
[data-testid="stStatusWidgetRunningManIcon"],
[data-testid="stStatusWidgetNewYearsIcon"] {
    visibility: hidden;
}
[data-testid="stStatusWidgetRunningIcon"]::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 16px;
    height: 16px;
    margin: -8px 0 0 -8px;
    border: 2px solid #E5E1D8;
    border-top-color: #A61C33;
    border-radius: 50%;
    animation: mfbc-spin 0.8s linear infinite;
}
@keyframes mfbc-spin {
    to { transform: rotate(360deg); }
}

/* Tabs */
button[data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.8rem;
    letter-spacing: 0.03em;
}
[data-baseweb="tab-highlight"] {
    background-color: #A61C33 !important;
}

/* The data editor's built-in "Delete row(s)" toolbar icon is tiny and
   grey by default — recolor it red and give it a hover background so
   it reads as the higher-stakes action it is. */
button[aria-label="Delete row(s)"] {
    color: #A61C33;
}
button[aria-label="Delete row(s)"]:hover {
    background-color: #FBE7EA;
}
button[aria-label="Delete row(s)"] svg {
    width: 20px;
    height: 20px;
}

hr {
    border-color: #D8D3C6 !important;
}
</style>
"""


def inject_global_css():
    st.html(CSS)


def page_header(title: str, subtitle: str = ""):
    subtitle_html = f'<div class="mfbc-header-subtitle">{subtitle}</div>' if subtitle else ""
    st.html(
        f'<div class="mfbc-header"><div class="mfbc-badge">MFBC</div>'
        f'<div><p class="mfbc-header-title">{title}</p>{subtitle_html}</div></div>'
    )
