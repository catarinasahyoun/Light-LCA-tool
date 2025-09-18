"""Authentication UI components."""

import streamlit as st
from ..auth.auth_manager import AuthManager
from ..utils.i18n import Translator

class AuthComponents:
    """UI components for authentication."""
    
    @staticmethod
    def render_sign_in():
        """Render the sign-in form."""
        st.markdown("### Sign In To Continue.")
        
        col1, col2 = st.columns([0.55, 0.45])
        
        with col1:
            with st.form("signin_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Sign In")
                
                if submit:
                    if not email or not password:
                        st.error("Please enter both email and password.")
                    else:
                        user = AuthManager.authenticate(email, password)
                        if user:
                            AuthManager.login_user(user)
                            st.success("Signed in successfully!")
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
        
        with col2:
            st.markdown("**Need Changes?**")
            st.markdown("User creation is disabled for now. Contact the admin to modify user details.")
    
    @staticmethod
    def check_authentication() -> bool:
        """Check if user is authenticated and handle sign-in if not."""
        user = AuthManager.get_current_user()
        if not user:
            AuthComponents.render_sign_in()
            return False
        return True