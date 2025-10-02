import io
import re
import json
import pandas as pd
import streamlit as st
import plotly.express as px  # for charts

class ResultsPage:
    @staticmethod
    def _safe_slug(name: str) -> str:
        name = (name or "").strip().replace(" ", "_")
        return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "Unnamed_Project"

    @staticmethod
    def render():
        """Public entry point used by app.py"""
        # Tabs in your requested order/titles
        tab_comp, tab_summary, tab_report = st.tabs([
            "📊 Comparison & Visualizations",
            "🧾 Results Summary",
            "📄 Report",
        ])

        with tab_comp:
            ResultsPage._render_charts_section()

        with tab_summary:
            ResultsPage._render_summary_section()

        with tab_report:
            ResultsPage._render_report_section(R=None)

    # ---------- 1) COMPARISON & VISUALIZATIONS (first tab) ----------
    @staticmethod
    def _render_charts_section():
        st.markdown("### Comparison & Visualizations")

        # Expect list[dict] like in your original app
        comparison_data = st.session_state.get("comparison_data", [])
        if not comparison_data:
            ResultsPage._show_missing_hint(["comparison_data"])
            return

        df_compare = pd.DataFrame(comparison_data)

        # Ensure expected columns exist
        expected_cols = {
            "Material",
            "CO2e per kg",
            "Recycled Content (%)",
            "Circularity (mapped)",
            "Lifetime (years)",
        }
        missing_cols = [c for c in expected_cols if c not in df_compare.columns]
        if missing_cols:
            st.warning(
                "The comparison dataset is missing columns: "
                + ", ".join(missing_cols)
                + ". Please check the Tool page logic that builds `comparison_data`."
            )

        # Helper: lifetime category
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

        my_color_sequence = ['#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']

        # Two rows of charts, like before
        col1, col2 = st.columns(2)

        # (A) CO2e per kg
        if {"Material", "CO2e per kg"}.issubset(df_compare.columns):
            with col1:
                fig_co2 = px.bar(
                    df_compare, x="Material", y="CO2e per kg",
                    color="Material", title="🏭 CO₂e per kg",
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
        if {"Material", "Recycled Content (%)"}.issubset(df_compare.columns):
            with col2:
                fig_recycled = px.bar(
                    df_compare, x="Material", y="Recycled Content (%)",
                    color="Material", title="♻️ Recycled Content ",
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
        if {"Material", "Circularity (mapped)"}.issubset(df_compare.columns):
            with col3:
                fig_circularity = px.bar(
                    df_compare, x="Material", y="Circularity (mapped)",
                    color="Material", title="🔄 Circularity ",
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
        if "Lifetime (years)" in df_compare.columns and "Material" in df_compare.columns:
            df_life = df_compare.copy()
            df_life["Lifetime Category"] = df_life["Lifetime (years)"].apply(lifetime_category)
            lifetime_cat_to_num = {"Short": 1, "Medium": 2, "Long": 3}
            df_life["Lifetime"] = df_life["Lifetime Category"].map(lifetime_cat_to_num)

            with col4:
                fig_lifetime = px.bar(
                    df_life, x="Material", y="Lifetime",
                    color="Material", title="⏱️ Lifetime ",
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

    # ---------- 2) RESULTS SUMMARY (second tab) ----------
    @staticmethod
    def _render_summary_section():
        # ======= Styles for boxed KPIs =======
        st.markdown(
            """
            <style>
              .kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
              @media(max-width: 1024px){ .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
              @media(max-width: 640px){ .kpi-grid { grid-template-columns: 1fr; } }
              .kpi-card {
                border: 1px solid #e0e0e0; border-radius: 12px; padding: 16px;
                background: #ffffff; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
              }
              .kpi-title { font-size: 13px; color: #2E7D32; margin: 0 0 8px 0; font-weight: 600; }
              .kpi-value { font-size: 22px; margin: 0; font-weight: 700; }
              .kpi-sub { font-size: 12px; color: #6b7280; margin-top: 6px; }
            </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Results Summary")

        # ---- Pull the numbers from session (or fallbacks) ----
        total_material_co2 = float(st.session_state.get("total_material_co2", 0.0) or 0.0)
        total_process_co2  = float(st.session_state.get("total_process_co2", 0.0) or 0.0)
        overall_co2        = float(st.session_state.get("overall_co2", total_material_co2 + total_process_co2) or 0.0)
        weighted_recycled  = float(st.session_state.get("weighted_recycled", 0.0) or 0.0)

        lifetime_weeks     = int(st.session_state.get("lifetime_weeks", 52) or 52)
        lifetime_years     = max(lifetime_weeks / 52.0, 1e-9)  # avoid div/zero

        # ---- Tree equivalent logic (no hard-coded 5 years) ----
        TREE_SEQUESTRATION_PER_YEAR = 22.0  # kg CO2 per tree per year (simple signal)

        mode = st.radio(
            "Tree equivalent basis",
            options=("Over lifetime", "Per year"),
            index=0,
            horizontal=True,
            key="trees_mode_select",
            help="Choose whether to express tree equivalent across the design's lifetime or per year.",
        )

        if mode == "Over lifetime":
            trees_equiv = overall_co2 / (TREE_SEQUESTRATION_PER_YEAR * lifetime_years)
            trees_label = f"{trees_equiv:.2f} trees over {lifetime_years:.1f} years"
            trees_sub   = f"22 kg CO₂/tree/year · lifetime={lifetime_years:.1f} years"
        else:
            trees_equiv = overall_co2 / TREE_SEQUESTRATION_PER_YEAR
            trees_label = f"{trees_equiv:.2f} trees / year"
            trees_sub   = "22 kg CO₂/tree/year"

        # ---- KPI Grid (boxed visuals) ----
        st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)

        # Weighted Recycled
        st.markdown(
            f"""
            <div class="kpi-card">
              <p class="kpi-title">Weighted Recycled Content</p>
              <p class="kpi-value">{weighted_recycled:.1f}%</p>
              <div class="kpi-sub">Mass-weighted across all selected materials</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Total CO2 - Materials
        st.markdown(
            f"""
            <div class="kpi-card">
              <p class="kpi-title">Total CO₂ — Materials</p>
              <p class="kpi-value">{total_material_co2:.2f} kg</p>
              <div class="kpi-sub">Sum of (mass × CO₂e/kg) per material</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Total CO2 - Processes
        st.markdown(
            f"""
            <div class="kpi-card">
              <p class="kpi-title">Total CO₂ — Processes</p>
              <p class="kpi-value">{total_process_co2:.2f} kg</p>
              <div class="kpi-sub">Sum of (amount × CO₂e/unit) for all steps</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Overall CO2
        st.markdown(
            f"""
            <div class="kpi-card">
              <p class="kpi-title">Overall CO₂</p>
              <p class="kpi-value">{overall_co2:.2f} kg</p>
              <div class="kpi-sub">Materials + Processes</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Tree Equivalent (mode-aware)
        st.markdown(
            f"""
            <div class="kpi-card">
              <p class="kpi-title">Tree Equivalent</p>
              <p class="kpi-value">{trees_label}</p>
              <div class="kpi-sub">{trees_sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Lifetime (display signal)
        st.markdown(
            f"""
            <div class="kpi-card">
              <p class="kpi-title">Lifetime</p>
              <p class="kpi-value">{lifetime_weeks} weeks</p>
              <div class="kpi-sub">{lifetime_years:.1f} years</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('</div>', unsafe_allow_html=True)

    # ---------- 3) REPORT (third tab; no “Export”) ----------
    @staticmethod
    def _render_report_section(R):
        st.markdown("### Report")

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
            st.write("**Totals keys present:**", [k for k, v in totals.items() if v is not None])
            st.write("**Comparison rows:**", len(df_compare))

    # ---------- helper: show what’s missing ----------
    @staticmethod
    def _show_missing_hint(required_keys):
        missing = [k for k in required_keys if not st.session_state.get(k)]
        if missing:
            st.warning(
                "No results found in session. The following keys are missing in `st.session_state`: "
                + ", ".join(missing)
                + ".\n\n"
                "Make sure your **Tool/Inputs** page sets these before visiting Results."
            )
        else:
            st.info("Nothing to display yet. Please run the Tool/Inputs page first.")
