"""Application settings and constants."""

import streamlit as st

# Visual Theme
BG = "#E4E5DA"       # Light Oat
POP = "#B485FF"      # Pop color for comparison charts

def initialize_session_state():
    """Initialize session state defaults. Call after st.set_page_config()."""
    if "lang" not in st.session_state:
        st.session_state.lang = "en"

    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

# Page configuration
PAGE_CONFIG = {
    "page_title": "TCHAI — Easy LCA Indicator",
    "page_icon": "🌿",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Default users for bootstrap
DEFAULT_USERS = [
    "sustainability@tchai.nl",
    "jillderegt@tchai.nl", 
    "veravanbeaumont@tchai.nl",
    "1"
]

DEFAULT_PASSWORD = "1"