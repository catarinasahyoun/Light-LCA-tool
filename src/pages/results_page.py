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

    # ---------- 3) REPORT (third tab; DOCX/PDF only, custom title, TCHAI logo) ----------
    @staticmethod
    def _render_report_section(R):
        import base64
        from io import BytesIO

        # Optional libraries: python-docx for DOCX; reportlab for PDF (if installed)
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
        except Exception as e:
            st.error("Missing dependency: `python-docx` is required to export DOCX reports.")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            REPORTLAB_AVAILABLE = True
        except Exception:
            REPORTLAB_AVAILABLE = False

        st.markdown("### Report")

        # ---------- gather data ----------
        project_name = st.session_state.get("project_name") or (
            (R or {}).get("project_name") if isinstance(R, dict) else None
        )
        project_name = ResultsPage._safe_slug(project_name or "Unnamed_Project")

        final_summary_html = (
            st.session_state.get("final_summary_html")
            or ((R or {}).get("final_summary_html") if isinstance(R, dict) else "")
        ) or "<h3>No summary available</h3>"

        comparison_data = (
            st.session_state.get("comparison_data")
            or ((R or {}).get("comparison_data") if isinstance(R, dict) else [])
        )

        totals = {
            "total_material_co2": st.session_state.get("total_material_co2"),
            "total_process_co2": st.session_state.get("total_process_co2"),
            "overall_co2": st.session_state.get("overall_co2"),
            "weighted_recycled": st.session_state.get("weighted_recycled"),
            "trees_equiv": st.session_state.get("trees_equiv"),
            "lifetime_weeks": st.session_state.get("lifetime_weeks"),
        }

        # ---------- UI controls: title + format ----------
        default_title = f"TCHAI Report — {project_name}"
        report_title = st.text_input("Report title", value=default_title, key="report_title_input")

        fmt_options = ["DOCX (.docx)"] + (["PDF (.pdf)"] if REPORTLAB_AVAILABLE else [])
        report_choice = st.selectbox("Format", fmt_options, index=0, key="report_format_choice")

        if not REPORTLAB_AVAILABLE:
            st.caption("To enable PDF export, install `reportlab` in your environment.")

        # ---------- locate logo (try a few common paths) ----------
        def _load_logo_bytes():
            candidate_paths = [
                "assets/logo/tchai_logo.png",            # your repo path if you have one
                "assets/tchai_logo.png",
                "tchai_logo.png",
                "/mnt/data/tchai_logo.png",              # provided path from your environment
            ]
            for p in candidate_paths:
                try:
                    with open(p, "rb") as f:
                        return f.read()
                except Exception:
                    continue
            return None

        logo_bytes = _load_logo_bytes()

        # ---------- builders ----------
        def build_docx() -> bytes:
            doc = Document()
            sec = doc.sections[0]
            sec.top_margin = Inches(0.75)
            sec.bottom_margin = Inches(0.75)
            sec.left_margin = Inches(0.75)
            sec.right_margin = Inches(0.75)

            # Logo header
            if logo_bytes:
                tmp = BytesIO(logo_bytes)
                try:
                    doc.add_picture(tmp, width=Inches(1.4))
                    last = doc.paragraphs[-1]
                    last.alignment = WD_ALIGN_PARAGRAPH.LEFT
                except Exception:
                    pass

            # Title
            p = doc.add_paragraph()
            run = p.add_run(report_title)
            run.bold = True
            run.font.size = Pt(20)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            # Project
            p2 = doc.add_paragraph()
            r2 = p2.add_run(f"Project: {project_name}")
            r2.font.size = Pt(11)

            # Divider
            doc.add_paragraph("")  # spacer

            # KPIs block
            doc.add_paragraph("Key Figures").runs[0].bold = True
            kpi = doc.add_table(rows=0, cols=2)
            kpi.style = "Light Grid"
            def add_row(lbl, val):
                row = kpi.add_row().cells
                row[0].text = lbl
                row[1].text = val

            def fmt(v, unit="kg"):
                return f"{v:.2f} {unit}"

            if totals["total_material_co2"] is not None:
                add_row("Total CO₂ — Materials", fmt(float(totals["total_material_co2"])))
            if totals["total_process_co2"] is not None:
                add_row("Total CO₂ — Processes", fmt(float(totals["total_process_co2"])))
            if totals["overall_co2"] is not None:
                add_row("Overall CO₂", fmt(float(totals["overall_co2"])))
            if totals["weighted_recycled"] is not None:
                add_row("Weighted Recycled Content", f"{float(totals['weighted_recycled']):.1f} %")
            if totals["lifetime_weeks"] is not None:
                yrs = float(totals["lifetime_weeks"]) / 52.0
                add_row("Lifetime", f"{int(totals['lifetime_weeks'])} weeks ({yrs:.1f} years)")

            doc.add_paragraph("")  # spacer

            # Comparison table (compact)
            if comparison_data:
                doc.add_paragraph("Comparison Data (excerpt)").runs[0].bold = True
                df = pd.DataFrame(comparison_data)
                # Limit columns to the most relevant if present
                cols_pref = ["Material", "CO2e per kg", "Recycled Content (%)", "Circularity (mapped)", "Lifetime (years)"]
                cols_show = [c for c in cols_pref if c in df.columns] or list(df.columns)[:5]
                df = df[cols_show].copy()

                table = doc.add_table(rows=1, cols=len(cols_show))
                hdr_cells = table.rows[0].cells
                for j, col in enumerate(cols_show):
                    hdr_cells[j].text = str(col)

                for _, row in df.iterrows():
                    cells = table.add_row().cells
                    for j, col in enumerate(cols_show):
                        cells[j].text = str(row[col])

                doc.add_paragraph("")  # spacer

            # Notes / HTML summary as plain text
            doc.add_paragraph("Notes").runs[0].bold = True
            # Strip tags for plain insertion
            plain_summary = re.sub("<[^<]+?>", "", final_summary_html or "")
            doc.add_paragraph(plain_summary or "—")

            # Save to bytes
            buf = BytesIO()
            doc.save(buf)
            return buf.getvalue()

        def build_pdf() -> bytes:
            buf = BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            width, height = A4
            x_margin = 50
            y = height - 60

            # Logo
            if logo_bytes:
                try:
                    from reportlab.lib.utils import ImageReader
                    img = ImageReader(BytesIO(logo_bytes))
                    c.drawImage(img, x_margin, y - 40, width=100, preserveAspectRatio=True, mask='auto')
                except Exception:
                    pass

            # Title
            c.setFont("Helvetica-Bold", 16)
            c.drawString(x_margin, y - 70, report_title)

            # Project
            c.setFont("Helvetica", 10)
            c.drawString(x_margin, y - 90, f"Project: {project_name}")

            # KPIs
            y_kpi = y - 120
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x_margin, y_kpi, "Key Figures")
            c.setFont("Helvetica", 10)
            y_kpi -= 16

            def draw_kpi(lbl, val):
                nonlocal y_kpi
                c.drawString(x_margin, y_kpi, f"{lbl}: {val}")
                y_kpi -= 14

            def fmt(v, unit="kg"):
                return f"{v:.2f} {unit}"

            if totals["total_material_co2"] is not None:
                draw_kpi("Total CO₂ — Materials", fmt(float(totals["total_material_co2"])))
            if totals["total_process_co2"] is not None:
                draw_kpi("Total CO₂ — Processes", fmt(float(totals["total_process_co2"])))
            if totals["overall_co2"] is not None:
                draw_kpi("Overall CO₂", fmt(float(totals["overall_co2"])))
            if totals["weighted_recycled"] is not None:
                draw_kpi("Weighted Recycled Content", f"{float(totals['weighted_recycled']):.1f} %")
            if totals["lifetime_weeks"] is not None:
                yrs = float(totals["lifetime_weeks"]) / 52.0
                draw_kpi("Lifetime", f"{int(totals['lifetime_weeks'])} weeks ({yrs:.1f} years)")

            # Footer
            c.setFont("Helvetica-Oblique", 8)
            c.drawRightString(width - x_margin, 30, "Generated with TCHAI LCA Tool")

            c.showPage()
            c.save()
            return buf.getvalue()

        # ---------- build + download ----------
        if report_choice.startswith("DOCX"):
            data_bytes = build_docx()
            file_name = f"{ResultsPage._safe_slug(report_title)}.docx"
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:  # PDF
            if not REPORTLAB_AVAILABLE:
                st.error("PDF export is not available because `reportlab` is not installed.")
                return
            data_bytes = build_pdf()
            file_name = f"{ResultsPage._safe_slug(report_title)}.pdf"
            mime = "application/pdf"

        st.download_button(
            label=f"⬇️ Download {file_name}",
            data=data_bytes,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
        )

        # Debug (optional)
        with st.expander("🔎 Debug details"):
            st.write("**Chosen title:**", report_title)
            st.write("**Format:**", report_choice)
            st.write("**Has logo:**", logo_bytes is not None)
            st.write("**Project:**", project_name)
