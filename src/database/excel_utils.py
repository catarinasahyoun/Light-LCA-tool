"""Excel file utilities and caching."""

import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Optional

class ExcelUtils:
    """Utilities for working with Excel files."""
    
    @staticmethod
    @st.cache_resource(show_spinner=False)
    def open_excel_cached(path_str: str, mtime: float) -> pd.ExcelFile:
        """Open an Excel file with caching based on modification time."""
        return pd.ExcelFile(path_str)
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def df_signature(df: pd.DataFrame) -> str:
        """Generate a signature for DataFrame caching."""
        return f"{df.shape}_{hash(tuple(df.columns))}"
    
    @staticmethod
    def find_sheet(xls: pd.ExcelFile, target: str) -> Optional[str]:
        """Find a sheet by name with fuzzy matching."""
        import re
        
        names = xls.sheet_names
        
        # Exact match
        for name in names:
            if name.lower() == target.lower():
                return name
        
        # Remove spaces and try again
        target_normalized = re.sub(r"\s+", "", target.lower())
        for name in names:
            if re.sub(r"\s+", "", name.lower()) == target_normalized:
                return name
        
        # Partial match
        for name in names:
            if target.lower() in name.lower():
                return name
        
        return None
    
    @staticmethod
    def load_excel(path: Path) -> Optional[pd.ExcelFile]:
        """Load an Excel file if it exists."""
        if path and path.exists():
            try:
                mtime = path.stat().st_mtime
                return ExcelUtils.open_excel_cached(str(path), mtime)
            except Exception:
                return None
        return None