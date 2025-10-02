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
from pathlib import Path
import streamlit as st

# --------------------------------------------------------------------
# Add src directory to Python path for Streamlit Cloud compatibility
# --------------------------------------------------------------------
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# --------------------------------------------------------------------
# Core configuration and setup components
# --------------------------------------------------------------------
from src.config import PAGE_CONFIG, setup_logging, initialize_session_state
from src.config.paths import ensure_dir

# Authentication and security components
from src.auth import AuthManager

# User interface and presentation components
from src.ui import UIStyles, Sidebar, Header, AuthComponents

# Internationalization support
from src.utils.i18n import Translator

# Application pages and views
from src.pages.tool_page import ToolPage
from src.pages.results_page import ResultsPage
from src.pages.user_guide_page import UserGuidePage
from src.pages.settings_page import SettingsPage
from src.pages.versions_page import VersionsPage

# --------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------
st.set_page_config(**PAGE_CONFIG)


def main():
    """
    Main application function that initializes and runs the TCHAI LCA Tool.

    Lifecycle:
      1) Initialize session state
      2) Setup logging
      3) Apply UI theme
      4) Bootstrap authentication
      5) Init i18n
      6) Render sidebar + header
      7) Check authentication
      8) Route to selected page
    """
    # 1) Session state
    initialize_session_state()

    # 2) Logging
    logger = setup_logging()
    logger.info("TCHAI LCA Application started - Modular architecture v2.0")

    # 3) UI Theme
    UIStyles.apply_theme()

    # 4) Auth bootstrap
    AuthManager.bootstrap_users_if_needed()

    # 5) i18n
    t = Translator.t

    # 6) Sidebar navigation
    sidebar = Sidebar()
    page = sidebar.render()
    logger.debug(f"User navigated to page: {page}")

    # 6.5) Header
    header = Header()
    header.render()

    # 7) Authentication checkpoint
    if not AuthComponents.check_authentication():
        logger.info("Authentication failed - stopping execution")
        st.stop()

    # 8) Routing
    if page in (t("nav.tool", "Actual Tool"), "Inputs"):
        logger.debug("Rendering Tool/Input page")
        ToolPage.render()

    elif page in (t("nav.results", "Results"), "Workspace"):
        logger.debug("Rendering Results/Workspace page")
        ResultsPage.render()

    elif page == t("nav.user_guide", "User Guide"):
        logger.debug("Rendering User Guide page")
        UserGuidePage.render()

    elif page in (t("nav.settings", "Administrative Settings"), "Settings"):
        logger.debug("Rendering Settings page")
        SettingsPage.render()

    elif page in (t("nav.versions", "Version"), "📁 Versions"):
        logger.debug("Rendering Versions page")
        VersionsPage.render()

    else:
        logger.error(f"Unknown page requested: {page}")
        st.error(f"Unknown page: {page}")
        st.info("Please use the sidebar navigation to select a valid page.")


if __name__ == "__main__":
    main()
