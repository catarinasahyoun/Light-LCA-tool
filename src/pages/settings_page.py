"""Settings page for administrative functions."""

import streamlit as st
from ..database.db_manager import DatabaseManager
from ..config.logging_config import setup_logging

logger = setup_logging()

class SettingsPage:
    """Administrative settings page for database management."""
    
    @staticmethod
    def render():
        """Render the settings page."""
        st.subheader("Database Manager")
        st.caption("Upload your Excel ONCE. It becomes the active database until you change it here.")
        
        # Show current active database
        active = DatabaseManager.get_active_database_path()
        if active:
            st.success(f"Active database: **{active.name}**")
        else:
            st.warning("No active database set.")
        
        # Database upload form
        with st.form("db_upload_form", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Upload Excel (.xlsx) And Activate.", 
                type=["xlsx"], 
                key="db_upload"
            )
            submitted = st.form_submit_button("Upload & Activate")
        
        if submitted:
            if uploaded_file is None:
                st.warning("Please choose a .xlsx file first.")
            else:
                try:
                    success = DatabaseManager.upload_and_activate_database(uploaded_file)
                    if success:
                        st.success(f"Database '{uploaded_file.name}' uploaded and activated!")
                        logger.info(f"Database uploaded: {uploaded_file.name}")
                        st.rerun()
                    else:
                        st.error("Failed to upload database.")
                except Exception as e:
                    logger.exception("Database upload failed")
                    st.error(f"Error uploading database: {e}")