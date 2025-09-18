"""Sidebar component for navigation."""

import streamlit as st
from ..config.paths import LOGO_CANDIDATES
from ..utils.file_utils import FileUtils
from ..utils.i18n import Translator
from ..auth.auth_manager import AuthManager

class Sidebar:
    """Application sidebar for navigation and user controls."""
    
    def __init__(self):
        self.logo_bytes = FileUtils.load_logo_bytes(LOGO_CANDIDATES)
        self.t = Translator.t
    
    def render(self) -> str:
        """Render the sidebar and return the selected page."""
        with st.sidebar:
            # Logo
            logo_tag = FileUtils.create_logo_tag(self.logo_bytes, 64)
            st.markdown(
                f"<div style='display:flex;justify-content:center;margin-bottom:10px'>{logo_tag}</div>",
                unsafe_allow_html=True
            )
            
            user = AuthManager.get_current_user()
            if user:
                # Navigation
                page = st.radio(
                    "",
                    [
                        self.t("nav.user_guide", "User Guide"),
                        self.t("nav.tool", "Actual Tool"),
                        self.t("nav.results", "Results"),
                        self.t("nav.versions", "Version"),
                        self.t("nav.settings", "Administrative Settings"),
                    ]
                )
                
                
                # User info and logout
                st.markdown("---")
                st.markdown(f"**{user.email}**")
                if st.button("Sign Out"):
                    AuthManager.logout_user()
                    st.rerun()
                
                return page
            else:
                return "Sign In"
