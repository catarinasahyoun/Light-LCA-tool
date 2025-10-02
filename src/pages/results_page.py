"""Results page for displaying LCA assessment results."""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any
from ..utils.calculations import compute_results, extract_number
from ..reports import generate_pdf_report, generate_docx_report 
from ..config.settings import POP, BG
from ..config.paths import TEMPLATE
import logging

logger = logging.getLogger(__name__)


class ResultsPage:
    """Results page for displaying LCA assessment results."""
    
    def __init__(self):
        pass
    
    @staticmethod
    def render():
        """Render the complete results page."""
        st.markdown("## Results & Analysis")
        
        # Check if we have materials selected
        if not st.session_state.assessment.get('selected_materials'):
            st.info("Go to Actual Tool and add at least one material.")
            return
        
        # Compute results
        try:
            R = compute_results()
        except Exception as e:
            st.error(f"Error computing results: {str(e)}")
            return
        
        # Create tabs for different result views
        tab_labels = ["Results & Comparison", "Final Summary", "Report"]
        t0, t1, t2 = st.tabs(tab_labels)
        
        with t0:
            ResultsPage._render_results_comparison(R)
        
        with t1:
            ResultsPage._render_final_summary(R)
        
        with t2:
            ResultsPage._render_report_section(R)
    
    @staticmethod
    def _render_results_comparison(R: Dict[str, Any]):
        """Render the results and comparison tab"""
        # Summary metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total CO₂ (Materials)", f"{R['total_material_co2']:.1f} kg", help="Embodied carbon from materials only")
        c2.metric("Total CO₂ (Processes)", f"{R['total_process_co2']:.1f} kg", help="Sum of process steps: amount × factor")
        c3.metric("Recycled Content", f"{R['weighted_recycled']:.1f}%", help="Mass-weighted % of recycled inputs")

        df = pd.DataFrame(R['comparison'])
        if df.empty:
            st.info("No data yet.")
        else:
            def style(fig):
                fig.update_layout(
                    plot_bgcolor=BG, paper_bgcolor=BG,
                    font=dict(color="#000", size=14),
                    title_x=0.5, title_font_size=20
                )
                return fig
            
            a, b = st.columns(2)
            with a:
                fig = px.bar(df, x="Material", y="CO2e per kg", color="Material", title="CO₂e Per Kg", color_discrete_sequence=[POP])
                st.plotly_chart(style(fig), use_container_width=True)
            with b:
                fig = px.bar(df, x="Material", y="Recycled Content (%)", color="Material", title="Recycled Content (%)", color_discrete_sequence=[POP])
                st.plotly_chart(style(fig), use_container_width=True)
            
            c, d = st.columns(2)
            with c:
                fig = px.bar(df, x="Material", y="Circularity (mapped)", color="Material", title="Circularity", color_discrete_sequence=[POP])
                fig.update_yaxes(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High'])
                st.plotly_chart(style(fig), use_container_width=True)
            with d:
                g = df.copy()
                def life_cat(x):
                    v = extract_number(x)
                    return 'Short' if v < 5 else ('Medium' if v <= 15 else 'Long')
                g['Lifetime Category'] = g['Lifetime (years)'].apply(life_cat)
                MAP = {"Short":1, "Medium":2, "Long":3}
                g['Lifetime'] = g['Lifetime Category'].map(MAP)
                fig = px.bar(g, x="Material", y="Lifetime", color="Material", title="Lifetime", color_discrete_sequence=[POP])
                fig.update_yaxes(tickmode='array', tickvals=[1,2,3], ticktext=['Short','Medium','Long'])
                st.plotly_chart(style(fig), use_container_width=True)
    
    @staticmethod
    def _render_final_summary(R: Dict[str, Any]):
        """Render the final summary tab"""
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric'><div>Total Impact CO₂e.</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric'><div>Tree Equivalent / Year.</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric'><div>Total Trees.</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        st.markdown("<p style='margin-top:8px; font-size:0.95rem; color:#374151'><b>Tree Equivalent</b> is a communication proxy (assumes ~22 kg CO₂ per tree per year).</p>", unsafe_allow_html=True)

        st.markdown("#### End-Of-Life Summary.")
        if R['eol_summary']:
            for k, v in R['eol_summary'].items():
                st.write(f"• **{k}** — {v}")
        else:
            st.write("—")
    
    @staticmethod
    def _render_report_section(R: Dict[str, Any]):
        """Render the report generation tab"""
        project = st.text_input("Project Name", value="Sample Project")
        notes = st.text_area("Executive Notes")

        tpl_path = TEMPLATE
        if tpl_path:
            st.caption(f"Using report template: **{tpl_path}**")
        else:
            st.warning("No DOCX template found; will attempt PDF or DOCX fallback.")

        mime = "vnd.openxmlformats-officedocument.wordprocessingml.document" 
        gen_func = generate_docx_report
        report = gen_func(project, notes, R, 
                              st.session_state.assessment["selected_materials"], 
                              st.session_state.materials, 
                              st.session_state.assessment["material_masses"])
        st.success("Using attached DOCX template with live numbers.")
        st.download_button(
            "⬇️ Download Report (DOCX From Template)",
            data=report,
            # Get project name safely from session_state
import re
project_name = st.session_state.get("project_name", "Unnamed_Project")

# Clean it up for filename use
safe_project = re.sub(r"[^A-Za-z0-9._-]", "_", project_name.strip().replace(" ", "_"))

# Make sure report_format starts with a dot
if report_format and not report_format.startswith("."):
    report_format = f".{report_format}"

file_name = f"TCHAI_Report_{safe_project}{report_format}"

            mime=f"application/{mime}"
        )
        
