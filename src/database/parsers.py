"""Data parsers for materials and processes."""

import re
import pandas as pd
import streamlit as st
from typing import Dict, Optional
from decimal import Decimal, InvalidOperation
from .excel_utils import ExcelUtils

class DataParser:
    """Base class for data parsing utilities."""
    
    @staticmethod
    def extract_number(value):
        """Extract a number from various input types."""
        try:
            if pd.isna(value):
                return 0.0
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Remove common non-numeric characters and try conversion
                cleaned = re.sub(r'[^\d.,\-+]', '', value.replace(',', '.'))
                return float(Decimal(cleaned))
            return 0.0
        except (InvalidOperation, ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize DataFrame column names for consistent matching."""
        # Flatten MultiIndex headers if present
        if isinstance(df.columns, pd.MultiIndex):
            flattened = []
            for col in df.columns:
                parts = [str(part) for part in col if str(part) != 'nan']
                flattened.append(' '.join(parts).strip())
            df.columns = flattened
        else:
            df.columns = [str(col) for col in df.columns]
        
        def canonicalize(col: str) -> str:
            """Canonicalize column name for matching."""
            return re.sub(r'[^\w]', '', col.lower().strip())
        
        df.columns = [canonicalize(c) for c in df.columns]
        return df
    
    @staticmethod
    def pick_column(df: pd.DataFrame, aliases: list) -> Optional[str]:
        """Pick the best matching column from a list of aliases."""
        for alias in aliases:
            canonical = re.sub(r'[^\w]', '', alias.lower())
            if canonical in df.columns:
                return canonical
        return None

class MaterialParser(DataParser):
    """Parser for materials data from Excel sheets."""
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def parse_materials_cached(df: pd.DataFrame, signature: str) -> Dict:
        """Parse materials with caching based on DataFrame signature."""
        return MaterialParser.parse_materials(df)
    
    @staticmethod
    def parse_materials(df_raw: pd.DataFrame) -> Dict:
        """Parse materials from DataFrame with robust column matching."""
        if df_raw is None or df_raw.empty:
            return {}
        
        df = DataParser.normalize_columns(df_raw)
        
        # Define column aliases for robust matching
        name_aliases = [
            "materialname", "material", "name", "materialname",
            "materialdescription", "materialdescription", "description"
        ]
        co2_aliases = [
            "co2eperkg", "co2ekg", "co2e", "co2perkg", "co2", "co2kg",
            "carbonintensity", "carbonfactor", "carbonintensitykg",
            "emissionfactor", "co2efactor", "co2factor", "emissionfactorkg",
            "emission", "factor", "kgco2eperkg", "kgco2ekg",
            "ghg", "ghgfactor", "globalwarmingpotential", "co2eqperkg", "co2eqperkg",
            "kgco2eperkg", "kgco2ekg", "kgco2kg", "kgco2kg"
        ]
        rc_aliases = [
            "recycledcontent", "recycledcontent", "recycled", "recycled",
            "recycle", "recycledpct", "recycledpercent", "recycled"
        ]
        eol_aliases = ["eol", "endoflife", "endoflife", "endoflife", "endoflife", "eoldefault"]
        life_aliases = ["lifetime", "life", "lifespan", "lifetimeyears", "lifetimeyears"]
        circ_aliases = ["circularity", "circ", "circularitylevel"]
        
        col_name = DataParser.pick_column(df, name_aliases)
        col_co2 = DataParser.pick_column(df, co2_aliases)
        col_rc = DataParser.pick_column(df, rc_aliases)
        col_eol = DataParser.pick_column(df, eol_aliases)
        col_life = DataParser.pick_column(df, life_aliases)
        col_circ = DataParser.pick_column(df, circ_aliases)
        
        # Heuristic fallbacks
        if not col_co2:
            numeric_cols = [c for c in df.columns if df[c].dtype in ['int64', 'float64']]
            if numeric_cols:
                col_co2 = numeric_cols[0]
        
        if not col_name:
            text_cols = [c for c in df.columns if df[c].dtype == 'object']
            if text_cols:
                col_name = text_cols[0]
        
        if not col_name or not col_co2:
            return {}
        
        materials = {}
        for _, row in df.iterrows():
            name = str(row.get(col_name, "")).strip()
            if not name or name.lower() in ['nan', 'none', '']:
                continue
            
            materials[name] = {
                'CO₂e (kg)': DataParser.extract_number(row.get(col_co2, 0)),
                'Recycled Content': DataParser.extract_number(row.get(col_rc, 0)),
                'EoL': str(row.get(col_eol, "")).strip() or "Unknown",
                'Lifetime': DataParser.extract_number(row.get(col_life, 52)),
                'Circularity': str(row.get(col_circ, "")).strip() or "Unknown"
            }
        
        return materials

class ProcessParser(DataParser):
    """Parser for process data from Excel sheets."""
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def parse_processes_cached(df: pd.DataFrame, signature: str) -> Dict:
        """Parse processes with caching based on DataFrame signature."""
        return ProcessParser.parse_processes(df)
    
    @staticmethod
    def parse_processes(df_raw: pd.DataFrame) -> Dict:
        """Parse processes from DataFrame."""
        if df_raw is None or df_raw.empty:
            return {}
        
        df = DataParser.normalize_columns(df_raw)
        
        col_proc = DataParser.pick_column(df, [
            "processtype", "processtype", "process", "step", "operation", "processname", "name"
        ])
        col_co2 = DataParser.pick_column(df, [
            "co2e", "co2ekg", "co2", "emission", "factor", "co2efactor", 
            "emissionfactor", "emissionfactorkg"
        ])
        col_unit = DataParser.pick_column(df, [
            "unit", "uom", "units", "measure", "measurement"
        ])
        
        if not col_proc or not col_co2:
            return {}
        
        processes = {}
        for _, row in df.iterrows():
            proc_name = str(row.get(col_proc, "")).strip()
            if not proc_name or proc_name.lower() in ['nan', 'none', '']:
                continue
            
            processes[proc_name] = {
                'CO₂e': DataParser.extract_number(row.get(col_co2, 0)),
                'Unit': str(row.get(col_unit, "")).strip() or ""
            }
        
        return processes