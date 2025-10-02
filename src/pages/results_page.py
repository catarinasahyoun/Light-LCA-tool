import io
import re
import json
import pandas as pd
import streamlit as st

class ResultsPage:
    @staticmethod
    def _safe_slug(name: str) -> str:
        # Trim, replace spaces with underscores, and remove unsafe filename chars
        name = (name or "").strip().replace(" ", "_")
        return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "Unnamed_Project"

    @staticmethod
    def render():
        """Public entry point used by app.py"""
        ResultsPage._render_report_section(R=None)

    @staticmethod
    def _render_report_section(R):
        """
        R is expected to be a dict-like results object OR None.
        Falls back to st.session_state fields set in app.py / tool page.
        """
        st.markdown("### 📄 Export / Report")

        # -------- Get context from session/R safely --------
        project_name = st.session_state.get("project_name") or (
            (R or {}).get("project_name") if isinstance(R, dict) else None
        )
        project_name = ResultsPage._safe_slug(project_name or "Unnamed_Project")

        # final HTML summary (already built upstream)
        final_summary_html = (
            st.session_state.get("final_summary_html")
            or ((R or {}).get("final_summary_html") if isinstance(R, dict) else "")
        ) or "<h3>No summary available</h3>"

        # comparison data (for CSV/JSON export)
        comparison_data = (
            st.session_state.get("comparison_data")
            or ((R or {}).get("comparison_data") if isinstance(R, dict) else [])
        )
        df_compare = pd.DataFrame(comparison_data) if comparison_data else pd.DataFrame()

        # Optional totals
        totals = {
            "total_material_co2": st.session_state.get(
                "total_material_co2",
                (R or {}).get("total_material_co2") if isinstance(R, dict) else None,
            ),
            "total_process_co2": st.session_state.get(
                "total_process_co2",
                (R or {}).get("total_process_co2") if isinstance(R, dict) else None,
            ),
            "overall_co2": st.session_state.get(
                "overall_co2",
                (R or {}).get("overall_co2") if isinstance(R, dict) else None,
            ),
            "weighted_recycled": st.session_state.get(
                "weighted_recycled",
                (R or {}).get("weighted_recycled") if isinstance(R, dict) else None,
            ),
            "trees_equiv": st.session_state.get(
                "trees_equiv",
                (R or {}).get("trees_equiv") if isinstance(R, dict) else None,
            ),
            "lifetime_weeks": st.session_state.get(
                "lifetime_weeks",
                (R or {}).get("lifetime_weeks") if isinstance(R, dict) else None,
            ),
        }

        # -------- Report format & filename --------
        report_format = st.selectbox(
            "Choose report format", [".html", ".json", ".csv"], index=0, key="report_format_select"
        )

        # Normalize extension (ensure it starts with ".")
        if report_format and not report_format.startswith("."):
            report_format = f".{report_format}"

        file_name = f"TCHAI_Report_{project_name}{report_format}"

        # -------- Build file bytes based on format --------
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
<pre>{json.dumps({"project_name": project_name, "totals": totals, "comparison_data": comparison_data}, indent=2)}</pre>
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
