"""Internationalization utilities."""

import json
import streamlit as st
from typing import Optional
from ..config.paths import LANG_FILE_DIR

class Translator:
    """Handles translation and internationalization."""
    
    @staticmethod
    def t(key: str, default: Optional[str] = None) -> str:
        """Translate a key to the current language."""
        lang = st.session_state.get("lang", "en")
        path = LANG_FILE_DIR / f"{lang}.json"
        
        try:
            if path.exists():
                translations = json.loads(path.read_text(encoding="utf-8"))
                return translations.get(key, default or key)
        except Exception:
            pass
        
        return default or key
    
    @staticmethod
    def set_language(lang_code: str):
        """Set the current language."""
        st.session_state.lang = lang_code
    
    @staticmethod
    def get_language() -> str:
        """Get the current language code."""
        return st.session_state.get("lang", "en")