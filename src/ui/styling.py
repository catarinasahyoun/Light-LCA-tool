"""UI styling and theming."""

import streamlit as st
from ..config.settings import BG, POP
from ..config.paths import FONTS
from ..utils.file_utils import FileUtils

class UIStyles:
    """Manages UI styling and theme application."""
    
    @staticmethod
    def apply_theme():
        """Apply the custom theme styling to the Streamlit app."""
        font_css = FileUtils.embed_font_css(FONTS)
        
        theme_css = f"""
        <style>
          {font_css}
          /* Fallback to file URLs if data-URI missing */
          @font-face {{
            font-family: 'PP Neue Montreal';
            src: url('assets/fonts/PPNeueMontreal-Regular.woff2') format('woff2'),
                 url('assets/fonts/PPNeueMontreal-Regular.ttf') format('truetype');
            font-weight: 400;
            font-style: normal;
            font-display: swap;
          }}
          @font-face {{
            font-family: 'PP Neue Montreal';
            src: url('assets/fonts/PPNeueMontreal-Medium.woff2') format('woff2'),
                 url('assets/fonts/PPNeueMontreal-Medium.ttf') format('truetype');
            font-weight: 500;
            font-style: normal;
            font-display: swap;
          }}

          .stApp {{
            background: {BG};
            color: #000;
            font-family: 'PP Neue Montreal', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
          }}

          html, body, [class*="css"] {{ font-weight: 400; }}

          h1, h2, h3, h4, .brand-title, .stTabs [data-baseweb="tab"] p {{
            font-weight: 500 !important;
            text-transform: capitalize;
            letter-spacing: 0.2px;
          }}

          .stRadio > label, .stRadio div[role="radiogroup"] label p {{
            font-weight: 500;
            text-transform: capitalize;
          }}

          .metric {{
            border: 1px solid #111;
            border-radius: 12px;
            padding: 14px;
            text-align: center;
            background: rgba(255,255,255,0.6);
            backdrop-filter: blur(2px);
          }}

          .brand-title {{ font-size: 26px; text-align: center; }}

          .stSelectbox div[data-baseweb="select"],
          .stNumberInput input,
          .stTextInput input,
          .stTextArea textarea {{
            border: 1px solid #111;
            background: #fff;
          }}

          .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
            box-shadow: inset 0 -2px 0 0 {POP};
          }}
        </style>
        """
        
        st.markdown(theme_css, unsafe_allow_html=True)