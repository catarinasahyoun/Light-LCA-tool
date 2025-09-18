"""Database manager for handling Excel databases."""

import json
import streamlit as st
from pathlib import Path
from typing import Optional, List
from ..config.paths import DB_ROOT, ACTIVE_DB_FILE
from .excel_utils import ExcelUtils

class DatabaseManager:
    """Manages Excel database files and active database selection."""
    
    @staticmethod
    def list_databases() -> List[Path]:
        """List all Excel databases in the database directory."""
        return sorted(DB_ROOT.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    @staticmethod
    def set_active_database(path: Path):
        """Set the active database and persist the choice."""
        ACTIVE_DB_FILE.write_text(json.dumps({"path": str(path)}))
        st.session_state.active_db_path = str(path)
    
    @staticmethod
    def get_active_database_path() -> Optional[Path]:
        """Get the path to the active database."""
        # Check session state first
        sess = st.session_state.get("active_db_path")
        if sess and Path(sess).exists():
            return Path(sess)
        
        # Check persisted active database
        if ACTIVE_DB_FILE.exists():
            try:
                data = json.loads(ACTIVE_DB_FILE.read_text())
                path = Path(data["path"])
                if path.exists():
                    st.session_state.active_db_path = str(path)
                    return path
            except Exception:
                pass
        
        # Fallback to database_latest.xlsx
        latest_path = DB_ROOT / "database_latest.xlsx"
        if latest_path.exists():
            DatabaseManager.set_active_database(latest_path)
            return latest_path
        
        # Fallback to newest database
        databases = DatabaseManager.list_databases()
        if databases:
            DatabaseManager.set_active_database(databases[0])
            return databases[0]
        
        return None
    
    @staticmethod
    def load_active_excel():
        """Load the active Excel database."""
        path = DatabaseManager.get_active_database_path()
        return ExcelUtils.load_excel(path) if path else None
    
    @staticmethod
    def upload_and_activate_database(uploaded_file) -> bool:
        """Upload a new database file and set it as active."""
        try:
            # Generate unique filename
            import datetime
            suffix = datetime.datetime.now().strftime("%Y-%m-%d")
            filename = f"database_{suffix}.xlsx"
            new_path = DB_ROOT / filename
            latest_path = DB_ROOT / "database_latest.xlsx"
            
            # Save uploaded file
            new_path.write_bytes(uploaded_file.getvalue())
            latest_path.write_bytes(uploaded_file.getvalue())
            
            # Set as active
            DatabaseManager.set_active_database(latest_path)
            
            return True
        except Exception:
            return False