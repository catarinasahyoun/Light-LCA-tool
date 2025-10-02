"""
TCHAI LCA Tool - Main Application Entry Point

This module serves as the primary entry point for the TCHAI Life Cycle Assessment (LCA) 
application. It orchestrates the initialization of all core components and handles the 
main application flow including authentication, navigation, and page routing.

Architecture:
   The application follows a modular architecture with clear separation of concerns:
   
   1. Configuration Setup (config/)
   2. Authentication Layer (auth/)  
   3. UI Components (ui/)
   4. Page Routing (pages/)
   5. Business Logic (utils/, models/, database/)
   6. Report Generation (reports/)

Key Responsibilities:
   - Streamlit page configuration and setup
   - Logging system initialization
   - UI theme application
   - User authentication bootstrap
   - Navigation and page routing
   - Session state management

Flow:
   main() → configure → authenticate → navigate → render_page

Author: TCHAI Team
Version: 2.0 (Modular Architecture)
"""

import sys
import os, io
import os
import io
from pathlib import Path
import streamlit as st

# --- Global logo helpers ---
from pathlib import Path
import io

def load_tchai_logo_bytes():
"""Find the logo from stable repo paths first; fall back to /mnt/data."""
candidates = [
Path("assets/tchai_logo.png"),
Path("assets/logo/tchai_logo.png"),
Path("tchai_logo.png"),
Path("/mnt/data/tchai_logo.png"),  # ephemeral fallback
]
for p in candidates:
try:
if p.exists():
return p.read_bytes()
except Exception:
pass
return None

def show_global_logo():
"""Render the logo at the very top of the page (left-aligned)."""
logo_bytes = st.session_state.get("tchai_logo_bytes")
if not logo_bytes:
return
left, right = st.columns([1, 8])
with left:
st.image(logo_bytes, width=150)
with right:
# spacer to keep header tight
st.markdown("&nbsp;", unsafe_allow_html=True)

# Add src directory to Python path for Streamlit Cloud compatibility
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
sys.path.insert(0, str(src_dir))



import streamlit as st

# Core configuration and setup components
from src.config import PAGE_CONFIG, setup_logging, initialize_session_state
st.set_page_config(**PAGE_CONFIG)
from src.config.paths import ensure_dir

# Authentication and security components  
from src.auth import AuthManager

# User interface and presentation components
from src.ui import UIStyles, Sidebar, Header, AuthComponents

# Internationalization support
from src.utils.i18n import Translator

# Application pages and views
# Application pages and views
from src.pages.tool_page import ToolPage
from src.pages.results_page import ResultsPage
from src.pages.user_guide_page import UserGuidePage
from src.pages.settings_page import SettingsPage
from src.pages.versions_page import VersionsPage


def main():
"""
   Main application function that initializes and runs the TCHAI LCA Tool.
   
   This function handles the complete application lifecycle:
   1. Configures Streamlit with custom page settings
   2. Initializes logging system for debugging and monitoring
   3. Applies custom UI styling and theme
   4. Bootstraps the authentication system
   5. Sets up internationalization support
   6. Renders the user interface (sidebar, header)
   7. Handles authentication checks
   8. Routes users to appropriate pages based on navigation
   
   The function uses Streamlit's session state to maintain user context
   and provides a seamless single-page application experience.
   
   Raises:
       SystemExit: If authentication fails or critical errors occur
       
   Side Effects:
       - Modifies Streamlit session state
       - Creates log files in assets/logs/
       - May create user files and directories
   """
# Step 1: Configure Streamlit page with custom settings
# PAGE_CONFIG contains title, icon, layout, and other page settings
# st.set_page_config(**PAGE_CONFIG)

# Step 1.5: Initialize session state after page config
# Must be called after set_page_config() to avoid Streamlit API errors
initialize_session_state()

# Step 2: Initialize logging system for application monitoring
# Creates log files and configures log levels based on environment
logger = setup_logging()
logger.info("TCHAI LCA Application started - Modular architecture v2.0")

# Step 3: Apply custom UI styling and theme
# Loads custom CSS, fonts, and color schemes
UIStyles.apply_theme()

logo_bytes = load_tchai_logo_bytes()
st.session_state["tchai_logo_bytes"] = logo_bytes  # one source of truth for all pages
if logo_bytes:
# optional: also place the logo in the sidebar
st.sidebar.image(logo_bytes, width=140)

    if not logo_bytes:
        logger.warning("TCHAI logo not found — check assets/tchai_logo.png or src/assets/tchai_logo.png")


# Step 4: Bootstrap authentication system
# Creates default admin user if no users exist
# Initializes user database and security settings
AuthManager.bootstrap_users_if_needed()

# Step 5: Initialize translation system
# Set up internationalization support for multi-language UI
t = Translator.t

# Step 6: Render sidebar navigation
# Creates navigation menu and handles page selection
sidebar = Sidebar()
page = sidebar.render()
logger.debug(f"User navigated to page: {page}")

show_global_logo()

# Step 7: Render application header
# Displays logo, title, and user information
header = Header()
header.render()

# Step 8: Authentication checkpoint
# Verify user is logged in and has valid session
# Redirects to login if authentication fails
if not AuthComponents.check_authentication():
logger.info("Authentication failed - stopping execution")
st.stop()

# Step 9: Page routing based on user selection
# Route to appropriate page based on sidebar navigation
# Each page handles its own rendering and business logic

if page in (t("nav.tool", "Actual Tool"), "Inputs"):
# Main LCA data input and configuration page
logger.debug("Rendering Tool/Input page")
ToolPage.render()

elif page in (t("nav.results", "Results"), "Workspace"):
# LCA results analysis and visualization page
logger.debug("Rendering Results/Workspace page")
ResultsPage.render()

elif page == t("nav.user_guide", "User Guide"):
# Documentation and help page
logger.debug("Rendering User Guide page")
UserGuidePage.render()

elif page in (t("nav.settings", "Administrative Settings"), "Settings"):
# Administrative configuration page
logger.debug("Rendering Settings page")
SettingsPage.render()

elif page in (t("nav.versions", "Version"), "📁 Versions"):
# Version management and saved assessments page
logger.debug("Rendering Versions page")
VersionsPage.render()

else:
# Handle unknown page navigation
logger.error(f"Unknown page requested: {page}")
st.error(f"Unknown page: {page}")
st.info("Please use the sidebar navigation to select a valid page.")


if __name__ == "__main__":
main()
