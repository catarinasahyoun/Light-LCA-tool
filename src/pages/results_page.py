import io
import re
import json
import io
import textwrap
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

    # ---------- 3) REPORT (third tab; DOCX only, custom title, TCHAI logo top-left) ----------
    @staticmethod
    def _render_report_section(R):
        import io, re
        from io import BytesIO
        import pandas as pd
        import streamlit as st

        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.enum.table import WD_TABLE_ALIGNMENT
        except Exception:
            st.error("Missing dependency: install `python-docx` to export DOCX reports.")
            return

        st.markdown("### Report")

        # ---------- static reference text ----------
        INTRO_TEXT = (
            "At Tchai we build different: within every brand space we design we try to leave a "
            "positive mark on people and planet.\n"
            "Our Easy LCA tool helps us see the real footprint "
            "of a concept before it’s built: materials, transport, end of life. With those numbers "
            "we can adjust, swap, or simplify.\n"
            "By 2030 we want every solution we deliver to have a "
            "clear, positive influence. Tracking impact now is a practical step toward that goal."
        )

        TRACKS_TEXT = (
            "Within every design process, we aim to integrate sustainability as early and as broadly as possible. "
            "We deliberately take a wide-angle approach: to us, sustainability is the result of a series of choices "
            "and trade-offs, not a one-size-fits-all solution.\n"
            "For some organizations, the focus lies on CO2e emissions; "
            "for others, it's on circularity, reuse, or social responsibility. We believe that each organization follows "
            "its own sustainability journey.\n"
            "At this conceptual stage, we used a consistent design to evaluate each material’s environmental impact based on the following criteria:"
        )

        CRITERIA_BULLETS = [
            "CO2e emissions per unit (calculated over a projects lifespan)",
            "Recycled content (% of recycled vs. virgin material)",
            "Circularity potential (reusability, reparability, modularity)",
            "End-of-life considerations",
        ]

        CONSIDERATIONS_SCOPE = (
            "Beyond environmental metrics, material selection was guided by expected lifespan, durability, and resistance "
            "to vandalism. While these are not directly reflected in CO2e calculations, they significantly impact long-term "
            "performance and suitability.\n"
            "Transport emissions were excluded from this stage, as they depend on future decisions such as supplier and "
            "production location. Should we be involved in the production phase, these will be included in the final LCA.\n"
            "This comparison is indicative, aiming to generate early insight into the environmental implications of material "
            "choices, focusing solely on environmental aspects.\n"
            "Social criteria like working conditions and human rights, while not part of this assessment, are essential to "
            "our approach. At Tchai, we only collaborate with suppliers who uphold high standards of ethics, transparency, and "
            "labor rights.\n"
            "This methodology supports better-informed early decisions and promotes meaningful, well-rounded discussions "
            "about sustainability."
        )

        CONCLUSION_TEXT = (
            "Not every improvement appears in a CO2e score, but that doesn’t make it less important.\n"
            "This comparison doesn’t "
            "point to a single perfect material, and that’s the point. Each option presents distinct strengths and trade-offs. "
            "The real opportunity lies in combining these insights to shape a smarter, more sustainable design.\n"
            "The final design will likely use a mix of materials, balancing functionality, durability, and environmental impact. "
            "This analysis provides the foundation for that design process.\n"
            "Ultimately, the goal isn’t just to reduce numbers, but to pursue meaningful sustainability: selecting materials "
            "that perform well both environmentally and practically over time. These are not just optimizations for today, but "
            "decisions made with long-term responsibility in mind."
        )

        # ---------- gather dynamic data ----------
        def _safe_slug(name: str) -> str:
            name = (name or "").strip().replace(" ", "_")
            return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "Unnamed_Project"

        project_name = st.session_state.get("project_name") or (
            (R or {}).get("project_name") if isinstance(R, dict) else None
        )
        project_slug = _safe_slug(project_name or "Unnamed_Project")

        comparison_data = (
            st.session_state.get("comparison_data")
            or ((R or {}).get("comparison_data") if isinstance(R, dict) else [])
        )
        df_compare = pd.DataFrame(comparison_data) if comparison_data else pd.DataFrame()

        eol_summary = st.session_state.get("eol_summary", {})
        totals = {
            "total_material_co2": float(st.session_state.get("total_material_co2") or 0.0),
            "total_process_co2":  float(st.session_state.get("total_process_co2") or 0.0),
            "overall_co2":        float(st.session_state.get("overall_co2") or 0.0),
            "weighted_recycled":  float(st.session_state.get("weighted_recycled") or 0.0),
            "lifetime_weeks":     int(st.session_state.get("lifetime_weeks") or 52),
        }
        lifetime_years = max(totals["lifetime_weeks"] / 52.0, 1e-9)

        # Unique materials list
        material_list = sorted(df_compare["Material"].dropna().unique().tolist()) if "Material" in df_compare else []

        # ---------- UI controls ----------
        default_title = f"Easy LCA Tool Report — {project_slug}"
        report_title = st.text_input("Report title", value=default_title, key="report_title_input")

        # ---------- logo loader ----------
        def _load_logo():
            for p in [
                "/mnt/data/tchai_logo.png",
                "assets/logo/tchai_logo.png",
                "assets/tchai_logo.png",
                "tchai_logo.png",
            ]:
                try:
                    with open(p, "rb") as f:
                        return f.read()
                except Exception:
                    continue
            return None

        logo_bytes = _load_logo()

        # ---------- DOCX builder ----------
        def build_docx() -> bytes:
            doc = Document()
            sec = doc.sections[0]
            sec.top_margin = Inches(0.7)
            sec.bottom_margin = Inches(0.7)
            sec.left_margin = Inches(0.7)
            sec.right_margin = Inches(0.7)

            # Cover: logo top-left
            if logo_bytes:
                tmp = io.BytesIO(logo_bytes)
                try:
                    doc.add_picture(tmp, width=Inches(1.6))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.LEFT
                except Exception:
                    pass

            title_p = doc.add_paragraph()
            t = title_p.add_run(report_title)
            t.bold = True
            t.font.size = Pt(20)
            title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            meta = doc.add_paragraph(f"Project: {project_name or project_slug}   ·   Date: {pd.Timestamp.now():%Y-%m-%d}")
            meta.alignment = WD_ALIGN_PARAGRAPH.LEFT
            doc.add_paragraph("")

            # Sections
            def add_title(doc, text, size=16):
                p = doc.add_paragraph()
                r = p.add_run(text)
                r.bold = True
                r.font.size = Pt(size)
                r.font.color.rgb = RGBColor(0,0,0)
                return p

            # ----- Different tracks -----
            add_title(doc, "Different tracks, shared direction")
            for para in TRACKS_TEXT.split("\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())
            for bullet in CRITERIA_BULLETS:
                p = doc.add_paragraph(style="List Bullet")
                r = p.add_run(bullet)
                r.font.size = Pt(11)
                r.font.color.rgb = RGBColor(0,0,0)

            # ----- Materials Included -----
            add_title(doc, "Materials Included in the Analysis")
            if material_list:
                for m in material_list:
                    p = doc.add_paragraph(style="List Bullet")
                    r = p.add_run(m)
                    r.font.size = Pt(11)
                    r.font.color.rgb = RGBColor(0,0,0)
            else:
                doc.add_paragraph("—")

            # ----- Considerations & Scope -----
            add_title(doc, "Considerations and Scope")
            for para in CONSIDERATIONS_SCOPE.split("\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())

            # ----- Results Summary (KPIs) -----
            add_title(doc, "Results Summary (Key Figures)")
            tbl = doc.add_table(rows=0, cols=2)
            tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
            tbl.style = "Light Grid"
            
            def add_kpi(label, value):
                row = tbl.add_row().cells
                row[0].text = label
                row[1].text = value
            add_kpi("Weighted Recycled Content", f"{totals['weighted_recycled']:.1f} %")
            add_kpi("Total CO₂ — Materials", f"{totals['total_material_co2']:.2f} kg")
            add_kpi("Total CO₂ — Processes", f"{totals['total_process_co2']:.2f} kg")
            add_kpi("Overall CO₂", f"{totals['overall_co2']:.2f} kg")
            add_kpi("Tree Equivalent*", f"{(totals['overall_co2']/(22.0*lifetime_years)):.2f} trees over {lifetime_years:.1f} years")

            doc.add_paragraph("*Estimated number of trees required to sequester the CO₂e emissions over the project lifespan.")

            # ----- Material Comparison Overview -----
            add_title(doc, "Material Comparison Overview")
            cols = ["Material", "CO2e per Unit (kg CO2e)", "Avg. Recycled Content", "Circularity", "End-of-Life", "Tree Equivalent*"]
            table = doc.add_table(rows=1, cols=len(cols))
            table.style = "Light Grid"
            hdr = table.rows[0].cells
            for j, col in enumerate(cols):
                hdr[j].text = col

            for _, row in df_compare.iterrows():
                mat = str(row.get("Material", ""))
                co2 = float(row.get("CO2e per kg", 0.0) or 0.0)
                rec = row.get("Recycled Content (%)", "")
                circ = row.get("Circularity (text)", row.get("Circularity (mapped)", ""))
                eol = eol_summary.get(mat, "")
                tree_eq = co2/(22.0*lifetime_years) if lifetime_years > 0 else 0
                cells = table.add_row().cells
                cells[0].text = mat
                cells[1].text = f"{co2:.2f}"
                cells[2].text = f"{rec}" if rec == "" else f"{float(rec):.1f}%"
                cells[3].text = str(circ)
                cells[4].text = str(eol)
                cells[5].text = f"{tree_eq:.2f}"

            # ----- Conclusion -----
            add_title(doc, "Conclusion")
            for para in CONCLUSION_TEXT.split("\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())

            out = io.BytesIO()
            doc.save(out)
            return out.getvalue()

        # ---------- build + download (DOCX only) ----------
        data_bytes = build_docx()
        file_name = f"{_safe_slug(report_title)}.docx"
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        st.download_button(
            label=f"⬇️ Download {file_name}",
            data=data_bytes,
            file_name=file_name,
            mime=mime,
            use_container_width=True,
        )
