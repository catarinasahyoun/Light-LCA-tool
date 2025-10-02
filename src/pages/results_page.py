import io
import re
import json
import pandas as pd
import streamlit as st

class ResultsPage:
    
    # ----------------------------------------------------------------------
    # 1. NEW: The main public method called by app.py
    # ----------------------------------------------------------------------
    @staticmethod
    def render(R=None):
        """
        Public method to render the full Results Page UI.
        R is the optional results object, if passed.
        This resolves the AttributeError from app.py.
        """
        st.title("🌱 Light-LCA Tool Results")
        
        # You can use st.tabs to organize the results content
        tab1, tab2 = st.tabs(["📊 Key Results", "📄 Export & Report"])
        
        with tab1:
            st.info("Review the key environmental metrics for your project.")
            
            # --- Placeholder for Actual Results ---
            # You should replace this placeholder logic with calls to st.metric, st.dataframe, or st.charts
            # using data from st.session_state (like overall_co2, comparison_data, etc.)
            overall_co2 = st.session_state.get("overall_co2")
            
            if overall_co2 is not None:
                st.metric(
                    label="Overall Carbon Footprint (CO₂e)", 
                    value=f"{overall_co2:,.2f} kg", 
                    help="Total calculated Global Warming Potential (GWP)."
                )
                # Add your core charts and data displays here!
                st.subheader("Comparison Data")
                comparison_data = st.session_state.get("comparison_data", [])
                df_compare = pd.DataFrame(comparison_data)
                if not df_compare.empty:
                    st.dataframe(df_compare, use_container_width=True)
                else:
                    st.warning("No comparison data available in session.")
            else:
                st.error("Results are not yet available. Please run the calculation first.")

        with tab2:
            # Call your existing function to handle the report generation and download
            ResultsPage._render_report_section(R)

    # ----------------------------------------------------------------------
    # 2. Existing Utility Method
    # ----------------------------------------------------------------------
    @staticmethod
    def _safe_slug(name: str) -> str:
        # Trim, replace spaces with underscores, and remove unsafe filename chars
        name = (name or "").strip().replace(" ", "_")
        return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "Unnamed_Project"

    # ----------------------------------------------------------------------
    # 3. Existing Report Method (with minor optimization)
    # ----------------------------------------------------------------------
    @staticmethod
    def _render_report_section(R):
        """
        R is expected to be a dict-like results object OR None.
        Falls back to st.session_state fields set in app.py.
        """
        st.markdown("### 📄 Export / Report")

        # -------- Get context from session/R safely (Project Name) --------
        R_dict = R if isinstance(R, dict) else {}
        project_name = st.session_state.get("project_name") or R_dict.get("project_name")
        project_name = ResultsPage._safe_slug(project_name or "Unnamed_Project")

        # final HTML summary (already built in app.py)
        final_summary_html = (
            st.session_state.get("final_summary_html")
            or R_dict.get("final_summary_html", "")
        ) or "<h3>No summary available</h3>"

        # comparison data (for CSV/JSON export)
        comparison_data = st.session_state.get("comparison_data") or R_dict.get("comparison_data", [])
        df_compare = pd.DataFrame(comparison_data) if comparison_data else pd.DataFrame()

        # Optional: total numbers
        TOTAL_KEYS = [
             "total_material_co2", "total_process_co2", "overall_co2",
             "weighted_recycled", "trees_equiv", "lifetime_weeks"
        ]
        # Optimized: Use dictionary comprehension for cleaner state/dict fallback
        totals = {
             key: st.session_state.get(key, R_dict.get(key))
             for key in TOTAL_KEYS
        }

        # -------- Report format & filename --------
        report_format = st.selectbox("Choose report format", [".html", ".json", ".csv"], index=0, key="report_format_select")

        # Normalize extension (ensure it starts with ".")
        if report_format and not report_format.startswith("."):
            report_format = f".{report_format}"

        file_name = f"TCHAI_Report_{project_name}{report_format}"

        # -------- Build file bytes based on format (No change, as this was excellent) --------
        if report_format == ".html":
            # Wrap the summary HTML in a minimal document
            html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TCHAI Report — {project_name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
{final_summary_html}
<hr>
<section>
<h3>Data (JSON)</h3>
<pre>{json.dumps({ "project_name": project_name, "totals": totals, "comparison_data": comparison_data }, indent=2)}</pre>
</section>
</body>
</html>"""
            data_bytes = html_doc.encode("utf-8")
            mime = "text/html"

        elif report_format == ".json":
            payload = {
                "project_name": project_name,
                "totals": totals,
                "comparison_data": comparison_data,
                "final_summary_html": final_summary_html,
            }
            data_bytes = json.dumps(payload, indent=2).encode("utf-8")
            mime = "application/json"

        elif report_format == ".csv":
            # If no comparison data, create an empty CSV with a message row
            if df_compare.empty:
                df_compare = pd.DataFrame([{"note": "No comparison data available"}])
            buf = io.StringIO()
            df_compare.to_csv(buf, index=False)
            data_bytes = buf.getvalue().encode("utf-8")
            mime = "text/csv"

        else:
            st.error("Unsupported report format.")
            return

        # -------- Download button --------
        st.download_button(
            label=f"⬇️ Download {file_name}",
            data=data_bytes,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
        )

        # Helpful debug info (toggle)
        with st.expander("🔎 Debug details"):
            st.write("**Filename:**", file_name)
            st.write("**Project Name (sanitized):**", project_name)
            st.write("**Totals:**", totals)
            st.write("**Comparison Data Rows:**", len(df_compare))
