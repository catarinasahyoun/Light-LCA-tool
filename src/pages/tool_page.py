"""Main tool page for LCA assessment input."""

import streamlit as st
import pandas as pd
from typing import Optional
from ..database.db_manager import DatabaseManager
from ..database.parsers import MaterialParser, ProcessParser
from ..database.excel_utils import ExcelUtils
from ..models.assessment import Assessment
from ..config.logging_config import setup_logging

logger = setup_logging()

class ToolPage:
    """Main tool page for inputting LCA assessment data."""
    
    @staticmethod
    def _ensure_assessment_model():
        """Ensure assessment data is properly structured."""
        try:
            Assessment(**st.session_state.assessment)
        except Exception:
            st.session_state.assessment = Assessment().model_dump()
    
    @staticmethod
    def _load_excel_data(excel_file) -> Optional[pd.ExcelFile]:
        """Load Excel data from uploaded file or active database."""
        if excel_file is not None:
            try:
                return pd.ExcelFile(excel_file)
            except Exception as e:
                logger.exception("Override Excel open failed")
                st.error(f"Could not open the uploaded Excel: {e}")
                return None
        else:
            return DatabaseManager.load_active_excel()
    
    @staticmethod
    def _parse_sheets(xls: pd.ExcelFile, materials_sheet: str, processes_sheet: str):
        """Parse materials and processes from Excel sheets."""
        try:
            materials_df = pd.read_excel(xls, sheet_name=materials_sheet)
            processes_df = pd.read_excel(xls, sheet_name=processes_sheet)
            
            # Parse with caching
            mat_sig = ExcelUtils.df_signature(materials_df)
            proc_sig = ExcelUtils.df_signature(processes_df)
            
            st.session_state.materials = MaterialParser.parse_materials_cached(materials_df, mat_sig) or {}
            st.session_state.processes = ProcessParser.parse_processes_cached(processes_df, proc_sig) or {}
            
            return True
        except Exception as e:
            logger.exception("Read/parse failed")
            st.error(f"Could not read the selected sheets: {e}")
            return False
    
    @staticmethod
    def _render_database_section():
        """Render the database status and override section."""
        active_path = DatabaseManager.get_active_database_path()
        
        st.subheader("Database Status")
        if active_path:
            st.success(f"Active database: **{active_path.name}**")
        else:
            st.error("No active database found. Go to Administrative Settings → Database Manager.")
        
        st.caption("Optional: override for THIS session only")
        override = st.file_uploader(
            "Session Override (.xlsx).", 
            type=["xlsx"], 
            key="override_db"
        )
        
        return override
    
    @staticmethod
    def _render_sheet_selection(xls: pd.ExcelFile):
        """Render sheet selection interface."""
        auto_materials = ExcelUtils.find_sheet(xls, "Materials") or xls.sheet_names[0]
        auto_processes = ExcelUtils.find_sheet(xls, "Processes") or (
            xls.sheet_names[1] if len(xls.sheet_names) > 1 else xls.sheet_names[0]
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            materials_sheet = st.selectbox(
                "Materials Sheet.",
                options=xls.sheet_names,
                index=xls.sheet_names.index(auto_materials) if auto_materials in xls.sheet_names else 0
            )
        
        with col2:
            processes_sheet = st.selectbox(
                "Processes Sheet.",
                options=xls.sheet_names,
                index=xls.sheet_names.index(auto_processes) if auto_processes in xls.sheet_names else 0
            )
        
        return materials_sheet, processes_sheet
    
    @staticmethod
    def _render_lifetime_section():
        """Render lifetime input section."""
        st.subheader("Lifetime (Weeks).")
        st.session_state.assessment["lifetime_weeks"] = st.number_input(
            "",
            min_value=1,
            value=int(st.session_state.assessment.get("lifetime_weeks", 52))
        )
    
    @staticmethod
    def _render_material_selection():
        """Render material selection interface."""
        st.subheader("Materials & Processes.")
        materials = list(st.session_state.materials.keys())
        
        st.session_state.assessment["selected_materials"] = st.multiselect(
            "Select Materials.",
            options=materials,
            default=st.session_state.assessment.get("selected_materials", [])
        )
        
        if not st.session_state.assessment["selected_materials"]:
            st.info("Select at least one material to proceed.")
            return False
        
        return True
    
    @staticmethod
    def _render_material_details():
        """Render detailed material input forms."""
        for material in st.session_state.assessment["selected_materials"]:
            st.markdown(f"### {material}.")
            
            # Material mass input
            masses = st.session_state.assessment.setdefault("material_masses", {})
            mass_default = float(masses.get(material, 1.0))
            masses[material] = st.number_input(
                f"Mass Of {material} (kg).",
                min_value=0.0,
                value=mass_default,
                key=f"mass_{material}"
            )
            
            # Show material properties
            props = st.session_state.materials[material]
            st.caption(
                f"CO₂e/kg: {props['CO₂e (kg)']} · "
                f"Recycled %: {props['Recycled Content']} · "
                f"EoL: {props['EoL']}"
            )
            
            # Processing steps
            ToolPage._render_processing_steps(material)
    
    @staticmethod
    def _render_processing_steps(material: str):
        """Render processing steps for a material."""
        procs_data = st.session_state.assessment.setdefault("processing_data", {})
        steps = procs_data.setdefault(material, [])
        
        # Number of steps input
        num_steps = st.number_input(
            f"How Many Processing Steps For {material}?",
            min_value=0,
            max_value=10,
            value=len(steps),
            key=f"steps_{material}"
        )
        
        # Adjust steps list
        if num_steps < len(steps):
            steps[:] = steps[:int(num_steps)]
        else:
            for _ in range(int(num_steps) - len(steps)):
                steps.append({
                    "process": "",
                    "amount": 1.0,
                    "co2e_per_unit": 0.0,
                    "unit": ""
                })
        
        # Render each step
        for i in range(int(num_steps)):
            process_options = [''] + list(st.session_state.processes.keys())
            current_process = steps[i]['process'] if steps[i]['process'] in st.session_state.processes else ''
            index = process_options.index(current_process) if current_process in process_options else 0
            
            process = st.selectbox(
                f"Process #{i+1}.",
                options=process_options,
                index=index,
                key=f"proc_{material}_{i}"
            )
            
            if process:
                process_data = st.session_state.processes.get(process, {})
                amount = st.number_input(
                    f"Amount For '{process}' ({process_data.get('Unit', '')}).",
                    min_value=0.0,
                    value=float(steps[i].get('amount', 1.0)),
                    key=f"amt_{material}_{i}"
                )
                
                steps[i] = {
                    "process": process,
                    "amount": amount,
                    "co2e_per_unit": process_data.get('CO₂e', 0.0),
                    "unit": process_data.get('Unit', '')
                }
    
    @staticmethod
    def render():
        """Render the complete tool page."""
        # Initialize session state
        if "materials" not in st.session_state:
            st.session_state.materials = {}
        if "processes" not in st.session_state:
            st.session_state.processes = {}
        if "assessment" not in st.session_state:
            st.session_state.assessment = Assessment().model_dump()
        
        ToolPage._ensure_assessment_model()

        # ---- Compute results + publish to session_state (so Results tabs can read them) ----
        assess = st.session_state.assessment
        materials_db = st.session_state.materials or {}
        processes_db = st.session_state.processes or {}

        selected = assess.get("selected_materials", []) or []
        masses = assess.get("material_masses", {}) or {}
        proc_data = assess.get("processing_data", {}) or {}
        lifetime_weeks = int(assess.get("lifetime_weeks", 52) or 52)
        lifetime_years = lifetime_weeks / 52.0

        # Totals
        total_material_co2 = 0.0
        total_process_co2 = 0.0
        total_mass = 0.0
        recycled_mass = 0.0

        # Build comparison rows for charts
        comparison_rows = []
        for mat in selected:
            props = materials_db.get(mat, {}) or {}
            mass_kg = float(masses.get(mat, 0.0) or 0.0)

            # Material factors with safe defaults
            co2_per_kg = float(props.get("CO₂e (kg)", props.get("CO2e (kg)", 0.0) or 0.0))
            recycled_pct = float(props.get("Recycled Content", 0.0) or 0.0)

            # Optional: if you have a text circularity value in your DB, map it; else default 0..3
            circ_text = str(props.get("Circularity", "") or "").strip().lower()
            circ_map = {"not circular": 0, "low": 1, "medium": 2, "high": 3}
            circ_val = circ_map.get(circ_text, 0)

            #   Lifetime per-material if present; else use global
            mat_life_years = float(props.get("Lifetime (years)", lifetime_years) or lifetime_years)

            # Material CO2
            mat_co2 = mass_kg * co2_per_kg
            total_material_co2 += mat_co2

            # Processes for this material
            for step in (proc_data.get(mat, []) or []):
                p = processes_db.get(step.get("process", ""), {}) or {}
                step_amount = float(step.get("amount", 0.0) or 0.0)
                # Prefer step-stored factor; fallback to DB factor key "CO₂e" / "CO2e"
                step_factor = float(step.get("co2e_per_unit", p.get("CO₂e", p.get("CO2e", 0.0)) or 0.0))
                total_process_co2 += step_amount * step_factor

            # Recycled mass contribution
            total_mass += mass_kg
            recycled_mass += mass_kg * (recycled_pct / 100.0)

            # Row for comparison charts
            comparison_rows.append({
                "Material": mat,
                "CO2e per kg": co2_per_kg,
                "Recycled Content (%)": recycled_pct,
                "Circularity (mapped)": circ_val,
                "Lifetime (years)": mat_life_years,
            })

        overall_co2 = total_material_co2 + total_process_co2
        weighted_recycled = (recycled_mass / total_mass * 100.0) if total_mass > 0 else 0.0

        # Simple tree equivalent (approx sequestration ~22 kg CO2 per tree-year)
        TREE_SEQUESTRATION_PER_YEAR = 22.0
        trees_equiv = overall_co2 / (TREE_SEQUESTRATION_PER_YEAR * max(lifetime_years, 1e-9))

        # ---- Build a concise HTML summary (as your Results expects) ----
        final_summary_html = f"""
        <div style='padding:12px;border:1px solid #e0e0e0;border-radius:8px'>
          <h3 style="margin:0 0 8px 0;">Final Summary</h3>
          <ul style="margin:0 0 8px 20px;">
            <li><b>Total CO₂ – Materials:</b> {total_material_co2:.2f} kg</li>
            <li><b>Total CO₂ – Processes:</b> {total_process_co2:.2f} kg</li>
            <li><b>Overall CO₂:</b> {overall_co2:.2f} kg</li>
            <li><b>Weighted Recycled Content:</b> {weighted_recycled:.1f}%</li>
            <li><b>Tree Equivalent:</b> {trees_equiv:.2f} trees (over {lifetime_years:.1f} years)</li>
          </ul>
        </div>
        """

        # ---- Publish to session_state for the Results page ----
        st.session_state.final_summary_html   = final_summary_html
        st.session_state.comparison_data      = comparison_rows
        st.session_state.total_material_co2   = total_material_co2
        st.session_state.total_process_co2    = total_process_co2
        st.session_state.overall_co2          = overall_co2
        st.session_state.weighted_recycled    = weighted_recycled
        st.session_state.trees_equiv          = trees_equiv
        st.session_state.lifetime_weeks       = lifetime_weeks

        # Optional: project name (used for the Report filename)
        if "project_name" not in st.session_state:
            st.session_state.project_name = "Unnamed_Project"

        # Database section
        override_file = ToolPage._render_database_section()
        xls = ToolPage._load_excel_data(override_file)
        
        if not xls:
            st.error("No Excel could be opened. Go to Administrative Settings or use the override above.")
            st.stop()
        
        # Sheet selection
        materials_sheet, processes_sheet = ToolPage._render_sheet_selection(xls)
        
        # Parse data
        if not ToolPage._parse_sheets(xls, materials_sheet, processes_sheet):
            st.stop()
        
        # Validation
        parsed_materials = len(st.session_state.materials or {})
        parsed_processes = len(st.session_state.processes or {})
        
        if parsed_materials == 0:
            st.warning("No materials parsed. Check your columns: Material name/material/name + CO2e + (optional) Recycled/EoL/Lifetime/Circularity.")
            st.stop()
        
        if parsed_processes == 0:
            st.warning("No processes parsed. Ensure the 'Processes' sheet has columns like Process Type + CO2e + Unit (or aliases).")
        
        # Input sections
        ToolPage._render_lifetime_section()
        
        if ToolPage._render_material_selection():
            ToolPage._render_material_details()
            
            # Normalize assessment model after user inputs
            ToolPage._ensure_assessment_model()
