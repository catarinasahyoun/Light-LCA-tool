import io
import re
import json
import pandas as pd
import streamlit as st
import plotly.express as px  # needed for the charts

class ResultsPage:
    @staticmethod
    def _safe_slug(name: str) -> str:
        # Trim, replace spaces with underscores, and remove unsafe filename chars
        name = (name or "").strip().replace(" ", "_")
        return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "Unnamed_Project"

    @staticmethod
    def render():
        """Public entry point used by app.py"""
        ResultsPage._render_summary_section()
        ResultsPage._render_charts_section()
        ResultsPage._render_report_section(R=None)

    # ---------- 1) SUMMARY (pretty HTML generated upstream) ----------
    @staticmethod
    def _render_summary_section():
        st.markdown("## 🧾 Results Summary")
        final_summary_html = st.session_state.get("final_summary_html", "")
        if final_summary_html:
            st.markdown(final_summary_html, unsafe_allow_html=True)
        else:
            st.info("No summary available yet. Go to the Inputs/Tool page, complete the assessment, and generate results.")

    # ---------- 2) COMPARISON VISUALIZATIONS (same structure as before) ----------
    @staticmethod
    def _render_charts_section():
        st.markdown("## 📊 Comparison Visualizations")

        comparison_data = st.session_state.get("comparison_data", [])
        if not comparison_data:
            st.info("No comparison data found. After entering materials/processes on the Inputs page, return here.")
            return

        df_compare = pd.DataFrame(comparison_data)

        # Helper: add lifetime category like your original code
        def lifetime_category(lifetime_value):
            try:
                v = float(lifetime_value)
            except Exception:
                v = 0.0
            if v < 5:
                return "Short"
            elif v <= 15:
                return "Medium"
            else:
                return "Long"

        # If these columns exist, mirror the original visuals
        # Colors similar to your original theme
        my_color_sequence = ['#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']

        # Safeguards for missing columns
        # Expected: "Material", "CO2e per kg", "Recycled Content (%)",
        # "Circularity (mapped)", "Circularity (text)", "Lifetime (years)"
        available_cols = set(df_compare.columns)

        # Layout containers
        col1, col2 = st.columns(2)

        # (A) CO2e per kg
        if {"Material", "CO2e per kg"}.issubset(available_cols):
            with col1:
                fig_co2 = px.bar(
                    df_compare, x="Material", y="CO2e per kg",
                    color="Material", title="🏭 CO₂e per kg Comparison",
                    color_discrete_sequence=my_color_sequence
                )
                fig_co2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#2E7D32'),
                    title_font_size=18,
                    title_x=0.5
                )
                st.plotly_chart(fig_co2, use_container_width=True)
        else:
            with col1:
                st.info("Missing columns for CO₂e chart (need: Material, CO2e per kg).")

        # (B) Recycled Content
        if {"Material", "Recycled Content (%)"}.issubset(available_cols):
            with col2:
                fig_recycled = px.bar(
                    df_compare, x="Material", y="Recycled Content (%)",
                    color="Material", title="♻️ Recycled Content Comparison",
                    color_discrete_sequence=my_color_sequence
                )
                fig_recycled.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#2E7D32'),
                    title_font_size=18,
                    title_x=0.5
                )
                st.plotly_chart(fig_recycled, use_container_width=True)
        else:
            with col2:
                st.info("Missing columns for Recycled Content chart (need: Material, Recycled Content (%)).")

        col3, col4 = st.columns(2)

        # (C) Circularity
        if {"Material", "Circularity (mapped)"}.issubset(available_cols):
            with col3:
                fig_circularity = px.bar(
                    df_compare, x="Material", y="Circularity (mapped)",
                    color="Material", title="🔄 Circularity Comparison",
                    color_discrete_sequence=my_color_sequence
                )
                fig_circularity.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#2E7D32'),
                    title_font_size=18,
                    title_x=0.5,
                    yaxis=dict(
                        tickmode='array',
                        tickvals=[0, 1, 2, 3],
                        ticktext=['Not Circular', 'Low', 'Medium', 'High']
                    )
                )
                st.plotly_chart(fig_circularity, use_container_width=True)
        else:
            with col3:
                st.info("Missing columns for Circularity chart (need: Material, Circularity (mapped)).")

        # (D) Lifetime (Short/Medium/Long)
        # Recreate the category column if needed
        if "Lifetime (years)" in available_cols:
            df_life = df_compare.copy()
            df_life["Lifetime Category"] = df_life["Lifetime (years)"].apply(lifetime_category)
            lifetime_cat_to_num = {"Short": 1, "Medium": 2, "Long": 3}
            df_life["Lifetime"] = df_life["Lifetime Category"].map(lifetime_cat_to_num)

            with col4:
                fig_lifetime = px.bar(
                    df_life, x="Material", y="Lifetime",
                    color="Material", title="⏱️ Lifetime Comparison",
                    color_discrete_sequence=my_color_sequence
                )
                fig_lifetime.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#2E7D32'),
                    title_font_size=18,
                    title_x=0.5,
                    yaxis=dict(
                        tickmode='array',
                        tickvals=[1, 2, 3],
                        ticktext=["Short", "Medium", "Long"]
                    )
                )
                st.plotly_chart(fig_lifetime, use_container_width=True)
        else:
            with col4:
                st.info("Missing column for Lifetime chart (need: Lifetime (years)).")

    # ---------- 3) EXPORT / REPORT (safe filename + formats) ----------
    @staticmethod
    def _render_report_section(R):
        """
        R is optional dict with results; we rely primarily on st.session_state.
        """
        st.markdown("## 📄 Export / Report")

        # Project name
        project_name = st.session_state.get("project_name") or (
            (R or {}).get("project_name") if isinstance(R, dict) else None
        )
        project_name = ResultsPage._safe_slug(project_name or "Unnamed_Project")

        # Pull data to include in exports
        final_summary_html = (
            st.session_state.get("final_summary_html")
            or ((R or {}).get("final_summary_html") if isinstance(R, dict) else "")
        ) or "<h3>No summary available</h3>"

        comparison_data = (
            st.session_state.get("comparison_data")
            or ((R or {}).get("comparison_data") if isinstance(R, dict) else [])
        )
        df_compare = pd.DataFrame(comparison_data) if comparison_data else pd.DataFrame()

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

        # Choose format (keep your selectbox)
        report_format = st.selectbox(
            "Choose report format", [".html", ".json", ".csv"], index=0, key="report_format_select"
        )
        # Normalize extension to start with "."
        if report_format and not report_format.startswith("."):
            report_format = f".{report_format}"

        file_name = f"TCHAI_Report_{project_name}{report_format}"

        # Build payload
        if report_format == ".html":
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

        else:  # ".csv"
            if df_compare.empty:
                df_compare = pd.DataFrame([{"note": "No comparison data available"}])
            buf = io.StringIO()
            df_compare.to_csv(buf, index=False)
            data_bytes = buf.getvalue().encode("utf-8")
            mime = "text/csv"

        # Download button
        st.download_button(
            label=f"⬇️ Download {file_name}",
            data=data_bytes,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
        )

        # Debug info (helpful while wiring)
        with st.expander("🔎 Debug details"):
            st.write("**Filename:**", file_name)
            st.write("**Project Name (sanitized):**", project_name)
            st.write("**Totals:**", totals)
            st.write("**Comparison rows:**", len(df_compare))
