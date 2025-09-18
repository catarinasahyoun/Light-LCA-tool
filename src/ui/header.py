"""Header component for the application."""

import streamlit as st
from ..config.paths import LOGO_CANDIDATES
from ..utils.file_utils import FileUtils
from ..auth.auth_manager import AuthManager

class Header:
    """Application header component."""
    
    def __init__(self):
        self.logo_bytes = FileUtils.load_logo_bytes(LOGO_CANDIDATES)
    
    def render(self):
        """Render the header with logo, title, and user avatar."""
        cl, cm, cr = st.columns([0.18, 0.64, 0.18])
        
        with cl:
            logo_tag = FileUtils.create_logo_tag(self.logo_bytes, 86)
            st.markdown(logo_tag, unsafe_allow_html=True)
        
        with cm:
            st.markdown(
                "<div class='brand-title'>Easy LCA Indicator</div>", 
                unsafe_allow_html=True
            )
        
        with cr:
            user = AuthManager.get_current_user()
            if user:
                initials = user.get_initials()
                st.markdown(
                    f"<div style='text-align:center;margin-top:20px;font-weight:500;'>{initials}</div>",
                    unsafe_allow_html=True
                )