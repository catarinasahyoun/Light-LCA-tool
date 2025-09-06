# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
from datetime import datetime
from pathlib import Path
import os
from io import BytesIO

# =========================
# Optional export backends
# =========================
REPORTLAB_OK = False
DOCX_OK = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

try:
    from docx import Document
    DOCX_OK = True
except Exception:
    DOCX_OK = False


# =========================
# SAFE DIRS & HELPERS
# =========================
def ensure_dir(p: Path):
    if p.exists() and not p.is_dir():
        p.rename(p.with_name(p.name + f"_conflict_{datetime.now().strftime('%Y%m%d%H%M%S')}"))
    p.mkdir(parents=True, exist_ok=True)

BASE = Path.cwd()
ASSETS = BASE / "assets"; ensure_dir(ASSETS)
GUIDES = ASSETS / "guides"; ensure_dir(GUIDES)

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        try:
            st.experimental_rerun()
        except Exception:
            pass


# =========================
# PAGE CONFIG & THEME
# =========================
st.set_page_config(page_title="Easy LCA Indicator", page_icon="🌿", layout="wide")

custom_css = """
<style>
    .stApp { background: linear-gradient(135deg, #F1F8E9 0%, #E8F5E8 100%); }
    .primary-header {
        color: #2E7D32 !important; text-align: center; font-size: 3rem !important;
        font-weight: 700 !important; margin-bottom: 1.25rem !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    .version-section {
        background: linear-gradient(135deg, #E8F5E8 0%, #F1F8E9 100%);
        padding: 18px; border-radius: 12px; border: 2px solid #4CAF50; margin: 12px 0;
        box-shadow: 0 6px 16px rgba(76, 175, 80, 0.15);
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.95); padding: 18px; border-radius: 12px;
        border: 2px solid #81C784; text-align: center;
        box-shadow: 0 6px 18px rgba(129,199,132,0.2);
    }
    .chart-container {
        background: rgba(255,255,255,0.95); padding: 16px; border-radius: 12px;
        border: 2px solid #E0E0E0; box-shadow: 0 6px 18px rgba(0,0,0,0.08);
        margin-bottom: 16px;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<h1 class="primary-header">🌿 Easy LCA Indicator</h1>', unsafe_allow_html=True)


# =========================
# NAVIGATION
# =========================
with st.sidebar:
    st.markdown("## 🧭 Navigation")
    page = st.radio("Go to:", ["Assessment", "User Guide"], index=0)


# =========================
# VERSION MANAGEMENT CLASS
# =========================
class LCAVersionManager:
    def __init__(self, storage_dir: str = "lca_versions"):
        self.storage_dir = storage_dir
        self.metadata_file = os.path.join(storage_dir, "lca_versions_metadata.json")
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_metadata(self, metadata):
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def save_version(self, version_name, assessment_data, description=""):
        metadata = self._load_metadata()
        if version_name in metadata:
            return False, f"Version '{version_name}' already exists!"

        version_data = {
            'assessment_data': assessment_data,
            'timestamp': datetime.now().isoformat(),
            'description': description
        }
        filename = f"{version_name}.json"
        filepath = os.path.join(self.storage_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(version_data, f)

        metadata[version_name] = {
            'filename': filename,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'materials_count': len(assessment_data.get('selected_materials', [])),
            'total_co2': assessment_data.get('overall_co2', 0),
            'lifetime_weeks': assessment_data.get('lifetime_weeks', 52)
        }
        self._save_metadata(metadata)
        return True, f"Version '{version_name}' saved successfully!"

    def load_version(self, version_name):
        metadata = self._load_metadata()
        if version_name not in metadata:
            return None, f"Version '{version_name}' not found!"
        filename = metadata[version_name]['filename']
        filepath = os.path.join(self.storage_dir, filename)
        try:
            with open(filepath, 'r') as f:
                version_data = json.load(f)
            return version_data['assessment_data'], f"Version '{version_name}' loaded successfully!"
        except FileNotFoundError:
            return None, f"File for version '{version_name}' not found!"

    def list_versions(self):
        return self._load_metadata()

    def delete_version(self, version_name):
        metadata = self._load_metadata()
        if version_name not in metadata:
            return False, f"Version '{version_name}' not found!"
        filename = metadata[version_name]['filename']
        filepath = os.path.join(self.storage_dir, filename)
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
        del metadata[version_name]
        self._save_metadata(metadata)
        return True, f"Version '{version_name}' deleted successfully!"


# =========================
# SESSION INIT
# =========================
if "version_manager" not in st.session_state:
    st.session_state.version_manager = LCAVersionManager()
if "current_assessment_data" not in st.session_state:
    st.session_state.current_assessment_data = {}
if "final_summary_html" not in st.session_state:
    st.session_state.final_summary_html = ""


# =========================
# COMMON HELPERS
# =========================
def extract_number(value):
    try:
        return float(value)
    except Exception:
        s = str(value).replace(',', '.')
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def lifetime_category(lifetime_value):
    if lifetime_value < 5:
        return "Short"
    elif lifetime_value <= 15:
        return "Medium"
    else:
        return "Long"


# =========================
# REPORT BUILDERS
# =========================
def _material_rows_for_report(selected_materials, materials_dict, material_masses, lifetime_years):
    rows = []
    for m in selected_materials:
        props = materials_dict.get(m, {})
        mass = float(material_masses.get(m, 0.0))
        co2_per_kg = float(props.get("CO₂e (kg)", 0.0))
        co2_total = mass * co2_per_kg
        trees_mat = (co2_total / (22.0 * max(lifetime_years, 1e-9))) if lifetime_years else 0.0
        rows.append([
            m,
            f"{co2_total:.2f}",
            f"{float(props.get('Recycled Content', 0.0)):.0f}%",
            str(props.get("Circularity", "Unknown")),
            str(props.get("EoL", "Unknown")),
            f"{trees_mat:.1f}"
        ])
    return rows

def build_pdf_from_template(project, notes, summary, selected_materials, materials_dict, material_masses):
    if not REPORTLAB_OK:
        return None
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]; H1.fontSize = 18
    H2 = styles["Heading2"]; H2.fontSize = 14
    P  = styles["BodyText"]; P.leading = 15

    story = []
    story += [Paragraph(f"{project} — Easy LCA Report", H1), Spacer(1, 6)]
    story += [Paragraph("Introduction", H2),
              Paragraph("At Tchai we build different: within every brand space we design we try to leave a positive mark on people and planet. Our Easy LCA tool helps us see the real footprint of a concept before it’s built.", P),
              Spacer(1, 8)]

    story += [Paragraph("Key Metrics", H2)]
    story += [Paragraph(f"Lifetime: <b>{summary['lifetime_years']:.1f} years</b> ({int(summary['lifetime_years']*52)} weeks)", P)]
    story += [Paragraph(f"Total CO₂e: <b>{summary['overall_co2']:.1f} kg</b>", P)]
    story += [Paragraph(f"Weighted recycled content: <b>{summary['weighted_recycled']:.1f}%</b>", P)]
    story += [Paragraph(f"Trees/year: <b>{summary['trees_equiv']:.1f}</b> · Total trees: <b>{summary['total_trees_equiv']:.1f}</b>", P)]
    if notes:
        story += [Spacer(1, 6), Paragraph("Executive Notes", H2), Paragraph(notes, P)]

    story += [Spacer(1, 8), Paragraph("Material Comparison Overview", H2)]
    header = ["Material", "CO₂e per Unit (kg)", "Avg. Recycled Content", "Circularity", "End-of-Life", "Tree Equivalent*"]
    body = _material_rows_for_report(selected_materials, materials_dict, material_masses, summary["lifetime_years"])
    table = Table([header] + body, colWidths=[90, 90, 90, 80, 90, 80])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.6, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story += [table]
    story += [Spacer(1, 6), Paragraph("*Estimated number of trees required to sequester the CO₂e emissions from one unit over the selected years.", P)]
    story += [Spacer(1, 8), Paragraph("End-of-Life Summary", H2)]
    if summary["eol_summary"]:
        bullets = "<br/>".join([f"• <b>{k}</b>: {v}" for k, v in summary["eol_summary"].items()])
        story += [Paragraph(bullets, P)]
    else:
        story += [Paragraph("—", P)]

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes

def build_docx_fallback(project, notes, summary, selected_materials, materials_dict, material_masses):
    if not DOCX_OK:
        return None
    doc = Document()
    doc.add_heading(f"{project} — Easy LCA Report", 0)
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph("At Tchai we build different: within every brand space we design we try to leave a positive mark on people and planet. Our Easy LCA tool helps us see the real footprint of a concept before it’s built.")
    doc.add_heading("Key Metrics", level=1)
    doc.add_paragraph(f"Lifetime: {summary['lifetime_years']:.1f} years ({int(summary['lifetime_years']*52)} weeks)")
    doc.add_paragraph(f"Total CO₂e: {summary['overall_co2']:.1f} kg")
    doc.add_paragraph(f"Weighted recycled content: {summary['weighted_recycled']:.1f}%")
    doc.add_paragraph(f"Trees/year: {summary['trees_equiv']:.1f} · Total trees: {summary['total_trees_equiv']:.1f}")
    if notes:
        doc.add_heading("Executive Notes", level=2); doc.add_paragraph(notes)
    doc.add_heading("Material Comparison Overview", level=1)
    table = doc.add_table(rows=1, cols=6)
    hdr = table.rows[0].cells
    hdr[0].text = "Material"; hdr[1].text = "CO₂e per Unit"; hdr[2].text = "Avg. Recycled Content"; hdr[3].text = "Circularity"; hdr[4].text = "End-of-Life"; hdr[5].text = "Tree Equivalent*"
    for row in _material_rows_for_report(selected_materials, materials_dict, material_masses, summary["lifetime_years"]):
        r = table.add_row().cells
        for i, v in enumerate(row): r[i].text = str(v)
    doc.add_paragraph("*Estimated number of trees required to sequester the CO₂e emissions from one unit over the selected years.")
    doc.add_heading("End-of-Life Summary", level=1)
    if summary['eol_summary']:
        for k, v in summary['eol_summary'].items():
            doc.add_paragraph(f"• {k}: {v}")
    else:
        doc.add_paragraph("—")
    bio = BytesIO(); doc.save(bio); return bio.getvalue()


# =========================
# USER GUIDE PAGE
# =========================
def _read_docx_text(docx_path: Path) -> str | None:
    # Try python-docx
    try:
        import docx  # python-docx
        d = docx.Document(str(docx_path))
        parts = []
        for p in d.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        # basic tables
        for tbl in d.tables:
            if tbl.rows:
                header = [c.text.strip() for c in tbl.rows[0].cells]
                if any(header):
                    parts += ["", " | ".join(header), " | ".join(["---"] * len(header))]
                    for r in tbl.rows[1:]:
                        parts.append(" | ".join(c.text.strip() for c in r.cells))
                    parts.append("")
        return "\n\n".join(parts).strip()
    except Exception:
        pass
    # Try docx2txt
    try:
        import docx2txt
        txt = docx2txt.process(str(docx_path))
        return (txt or "").strip()
    except Exception:
        return None

def user_guide_page():
    st.subheader("User Guide")
    st.caption("Official guide is rendered inline below. If it’s missing, upload it once to store it persistently.")

    OFFICIAL_GUIDE_NAME = "LCA-Light Usage Overview - Updated.docx"
    primary = Path("/mnt/data") / OFFICIAL_GUIDE_NAME
    fallback = GUIDES / OFFICIAL_GUIDE_NAME

    guide_path = primary if primary.exists() else (fallback if fallback.exists() else None)
    if not guide_path:
        st.warning(f"Guide not found at `{primary}` or `{fallback}`.")
        up = st.file_uploader(f"Upload {OFFICIAL_GUIDE_NAME}", type=["docx"], key="guide_upload")
        if up is not None:
            try:
                ensure_dir(GUIDES)
                dest = fallback
                dest.write_bytes(up.read())
                st.success(f"Saved guide to {dest}. Reloading…")
                _rerun()
            except Exception as e:
                st.error(f"Failed to save guide: {e}")
        return

    text = _read_docx_text(guide_path)
    if text:
        st.text_area("", value=text, height=620, label_visibility="collapsed")
    else:
        st.warning("Found the guide file but couldn't extract text. Install **python-docx** or **docx2txt** to enable inline view.")

    try:
        with open(guide_path, "rb") as f:
            st.download_button(
                "⬇️ Download the User Guide (DOCX)",
                f,
                file_name=OFFICIAL_GUIDE_NAME,
                type="secondary",
                use_container_width=True,
            )
    except Exception:
        st.info("Download unavailable (couldn't open the DOCX file).")


# =========================
# ASSESSMENT PAGE
# =========================
def extract_material_data(sheet_df: pd.DataFrame):
    sheet_df = sheet_df.copy()
    sheet_df.columns = [str(c).strip() for c in sheet_df.columns]
    expected_columns = [
        "Material name", "CO2e (kg)", "Recycled Content", "EoL",
        "Lifetime", "Comment", "Circularity", "Alternative Material"
    ]
    for col in expected_columns:
        if col not in sheet_df.columns:
            st.error(f"Error: '{col}' column is missing in Materials sheet.")
            return {}
    out = {}
    for _, row in sheet_df.iterrows():
        name = str(row["Material name"]).strip() if pd.notna(row["Material name"]) else ""
        if not name:
            continue
        out[name] = {
            "CO₂e (kg)": extract_number(row["CO2e (kg)"]),
            "Recycled Content": extract_number(row["Recycled Content"]),
            "EoL": str(row["EoL"]).strip() if pd.notna(row["EoL"]) else "Unknown",
            "Lifetime": str(row["Lifetime"]).strip() if pd.notna(row["Lifetime"]) else "Unknown",
            "Comment": str(row["Comment"]).strip() if pd.notna(row["Comment"]) and str(row["Comment"]).strip() else "No comment",
            "Circularity": str(row["Circularity"]).strip() if pd.notna(row["Circularity"]) else "Unknown",
            "Alternative Material": str(row["Alternative Material"]).strip() if pd.notna(row["Alternative Material"]) else "None"
        }
    return out

def extract_processes_data(sheet_df: pd.DataFrame):
    df = sheet_df.copy()
    df.columns = [str(c).strip().replace("₂","2").replace("CO₂","CO2") for c in df.columns]
    proc_col = next((c for c in df.columns if 'process' in c.lower()), None)
    co2_col  = next((c for c in df.columns if 'co2' in c.lower()), None)
    unit_col = next((c for c in df.columns if 'unit' in c.lower()), None)
    if not proc_col or not co2_col or not unit_col:
        st.error("Error: Could not detect correct column names in 'Processes' sheet. Please check Excel formatting.")
        return {}
    out = {}
    for _, row in df.iterrows():
        proc_name = str(row[proc_col]).strip() if pd.notna(row[proc_col]) else ""
        if not proc_name:
            continue
        out[proc_name] = {
            "CO₂e": extract_number(row[co2_col]),
            "Unit": str(row[unit_col]).strip() if pd.notna(row[unit_col]) else "Unknown"
        }
    return out

def assessment_page():
    # Sidebar: Version management
    st.sidebar.markdown('<div class="version-section">', unsafe_allow_html=True)
    st.sidebar.markdown("## 📁 Version Management")
    version_action = st.sidebar.selectbox("Choose Action:", ["New Assessment", "Save Current", "Load Version", "Manage Versions"])

    if version_action == "Save Current":
        st.sidebar.markdown("### Save Current Assessment")
        version_name = st.sidebar.text_input("Version Name:", key="save_version_name")
        version_description = st.sidebar.text_area("Description (optional):", key="save_version_desc")
        if st.sidebar.button("💾 Save Version"):
            if version_name and st.session_state.current_assessment_data:
                ok, msg = st.session_state.version_manager.save_version(version_name, st.session_state.current_assessment_data, version_description)
                (st.sidebar.success if ok else st.sidebar.error)(msg)
            elif not version_name:
                st.sidebar.error("Please enter a version name")
            else:
                st.sidebar.error("No assessment data to save. Complete an assessment first.")

    elif version_action == "Load Version":
        st.sidebar.markdown("### Load Saved Version")
        versions = st.session_state.version_manager.list_versions()
        if versions:
            selected = st.sidebar.selectbox("Select Version:", list(versions.keys()))
            if selected:
                info = versions[selected]
                st.sidebar.write(f"**Description:** {info.get('description','—')}")
                st.sidebar.write(f"**Created:** {info.get('created_at','—')}")
                st.sidebar.write(f"**Materials:** {info.get('materials_count',0)}")
                st.sidebar.write(f"**Total CO₂:** {info.get('total_co2',0):.2f} kg")
                if st.sidebar.button("📂 Load Version"):
                    data, msg = st.session_state.version_manager.load_version(selected)
                    if data:
                        st.session_state.loaded_version_data = data
                        st.sidebar.success(msg)
                        st.sidebar.info("Data loaded! Scroll and continue; values pre-filled where applicable.")
                    else:
                        st.sidebar.error(msg)
        else:
            st.sidebar.info("No saved versions available")

    elif version_action == "Manage Versions":
        st.sidebar.markdown("### Manage Versions")
        versions = st.session_state.version_manager.list_versions()
        if versions:
            target = st.sidebar.selectbox("Select Version to Delete:", list(versions.keys()))
            if st.sidebar.button("🗑️ Delete Version", type="secondary"):
                ok, msg = st.session_state.version_manager.delete_version(target)
                (st.sidebar.success if ok else st.sidebar.error)(msg)
                if ok: st.rerun()
            st.sidebar.markdown("---")
            for name, info in versions.items():
                st.sidebar.write(f"**{name}**")
                st.sidebar.write(f"📅 {info.get('created_at','—')[:16]}")
                st.sidebar.write(f"📊 {info.get('materials_count',0)} materials")
                st.sidebar.write("---")
        else:
            st.sidebar.info("No versions to manage")
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # Global lifetime (with loaded default if available)
    default_lifetime = 52
    if hasattr(st.session_state, 'loaded_version_data') and 'lifetime_weeks' in st.session_state.loaded_version_data:
        default_lifetime = st.session_state.loaded_version_data['lifetime_weeks']
    lifetime_weeks = st.number_input("Enter the lifetime of the final product (in weeks):", min_value=1, value=default_lifetime, key="lifetime_weeks")
    lifetime_years = lifetime_weeks / 52

    # Upload database
    st.markdown("""
    <div class="chart-container">
        <h3 style="margin-top: 0; color: #2E7D32;">📂 Upload Your Excel Database</h3>
        <p style="margin-bottom: 0;">Upload your Excel file containing <b>Materials</b> and <b>Processes</b> sheets to begin the LCA assessment.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Excel Database", type=["xlsx"])
    if not uploaded_file:
        st.info("👆 Please upload your Excel database file to continue with the assessment.")
        return

    xls = pd.ExcelFile(uploaded_file)
    try:
        df_materials = pd.read_excel(xls, sheet_name="Materials")
        df_processes = pd.read_excel(xls, sheet_name="Processes")
    except ValueError as e:
        st.error(f"Missing sheet: {e}. Ensure your Excel has 'Materials' and 'Processes' sheets.")
        return

    materials_dict = extract_material_data(df_materials)
    processes_dict = extract_processes_data(df_processes)

    if not materials_dict:
        st.stop()

    # Material selection (pre-load if saved)
    default_materials = []
    if hasattr(st.session_state, 'loaded_version_data') and 'selected_materials' in st.session_state.loaded_version_data:
        default_materials = st.session_state.loaded_version_data['selected_materials']

    selected_materials = st.multiselect("Select Materials", options=list(materials_dict.keys()), default=default_materials)
    if not selected_materials:
        st.info("Please select at least one material.")
        return

    # Accumulators
    total_material_co2 = 0.0
    total_process_co2 = 0.0
    total_mass = 0.0
    total_weighted_recycled = 0.0
    eol_summary = {}
    comparison_data = []
    material_masses = {}
    processing_data = {}

    circularity_mapping = {"High": 3, "Medium": 2, "Low": 1, "Not Circular": 0}

    # Loop over materials
    for material_name in selected_materials:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader(f"🔧 {material_name}")
        props = materials_dict[material_name]

        # default mass if loaded
        default_mass = 1.0
        if (hasattr(st.session_state, 'loaded_version_data')
            and 'material_masses' in st.session_state.loaded_version_data
            and material_name in st.session_state.loaded_version_data['material_masses']):
            default_mass = float(st.session_state.loaded_version_data['material_masses'][material_name])

        mass = st.number_input(f"Enter mass of {material_name} (kg)", min_value=0.0, value=default_mass, key=f"mass_{material_name}")
        material_masses[material_name] = mass

        total_mass += mass
        mat_co2 = mass * props["CO₂e (kg)"]
        total_material_co2 += mat_co2
        total_weighted_recycled += mass * props["Recycled Content"]

        st.write(f"**CO₂e per kg:** {props['CO₂e (kg)']} kg")
        st.write(f"**Recycled Content:** {props['Recycled Content']}%")
        st.write(f"**Lifetime:** {props['Lifetime']}")
        st.write(f"**Circularity:** {props['Circularity']}")
        st.write(f"**Comment:** {props['Comment']}")
        st.write(f"**Alternative Material:** {props['Alternative Material']}")

        eol_summary[material_name] = props["EoL"]

        # number of processing steps
        default_steps = 0
        if (hasattr(st.session_state, 'loaded_version_data')
            and 'processing_data' in st.session_state.loaded_version_data
            and material_name in st.session_state.loaded_version_data['processing_data']):
            default_steps = len(st.session_state.loaded_version_data['processing_data'][material_name])

        n_proc = int(st.number_input(f"How many processing steps for {material_name}?", min_value=0, max_value=10, value=default_steps, key=f"proc_steps_{material_name}"))

        proc_total = 0.0
        processing_data[material_name] = []

        for i in range(n_proc):
            default_process = ""
            default_amount = 1.0
            if (hasattr(st.session_state, 'loaded_version_data')
                and 'processing_data' in st.session_state.loaded_version_data
                and material_name in st.session_state.loaded_version_data['processing_data']
                and i < len(st.session_state.loaded_version_data['processing_data'][material_name])):
                loaded = st.session_state.loaded_version_data['processing_data'][material_name][i]
                default_process = loaded.get('process', "")
                default_amount = float(loaded.get('amount', 1.0))

            proc_selected = st.selectbox(f"Process #{i+1} for {material_name}",
                                         options=[""] + list(processes_dict.keys()),
                                         index=(list(processes_dict.keys()).index(default_process) + 1) if default_process in processes_dict else 0,
                                         key=f"process_{material_name}_{i}")
            if proc_selected:
                pprops = processes_dict.get(proc_selected, {})
                co2e_per_unit = pprops.get("CO₂e", 0.0)
                unit = pprops.get("Unit", "Unknown")
                amount = st.number_input(f"Enter amount for '{proc_selected}' ({unit})",
                                         min_value=0.0, value=default_amount, key=f"amount_{material_name}_{i}")
                proc_total += amount * co2e_per_unit
                processing_data[material_name].append({
                    'process': proc_selected, 'amount': amount,
                    'co2e_per_unit': co2e_per_unit, 'unit': unit
                })

        total_process_co2 += proc_total

        circ_val = circularity_mapping.get(props["Circularity"].title(), 0)
        life_num = extract_number(props["Lifetime"])
        comparison_data.append({
            "Material": material_name,
            "CO2e per kg": props["CO₂e (kg)"],
            "Recycled Content (%)": props["Recycled Content"],
            "Circularity (mapped)": circ_val,
            "Circularity (text)": props["Circularity"],
            "Lifetime (years)": life_num,
            "Lifetime (text)": props["Lifetime"]
        })

        st.markdown('</div>', unsafe_allow_html=True)

    # Final summary
    overall_co2 = total_material_co2 + total_process_co2
    total_trees_equiv = overall_co2 / 22
    trees_equiv = overall_co2 / (22 * (lifetime_years if lifetime_years else 1))
    weighted_recycled = (total_weighted_recycled / total_mass) if total_mass > 0 else 0.0

    final_summary_html = f"""
    <div class="chart-container">
        <h2 style="color:#2E7D32; text-align:center;">🌍 Final Summary</h2>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap: 16px;">
            <div class="metric-card"><h4>♻️ Weighted Recycled Content</h4><p>{weighted_recycled:.1f}%</p></div>
            <div class="metric-card"><h4>🏭 Total CO₂ (Materials)</h4><p>{total_material_co2:.1f} kg</p></div>
            <div class="metric-card"><h4>🔧 Total CO₂ (Processes)</h4><p>{total_process_co2:.1f} kg</p></div>
            <div class="metric-card"><h4>🌍 Total CO₂e</h4><p>{overall_co2:.1f} kg</p></div>
            <div class="metric-card"><h4>🌳 Trees / year</h4><p>{trees_equiv:.1f} over {lifetime_years:.1f} yrs</p></div>
            <div class="metric-card"><h4>🌳 Total Trees</h4><p>{total_trees_equiv:.1f}</p></div>
        </div>
        <h4 style="color:#2E7D32; margin-top:18px;">🔄 End-of-Life Summary</h4>
        <div style="background:rgba(255,255,255,0.75); padding:14px; border-radius:10px;">
            {"".join([f'<div>• <b>{k}</b>: {v}</div>' for k,v in eol_summary.items()])}
        </div>
    </div>
    """
    st.markdown(final_summary_html, unsafe_allow_html=True)

    # Store assessment in session for versioning & report
    st.session_state.current_assessment_data = {
        'lifetime_weeks': lifetime_weeks,
        'selected_materials': selected_materials,
        'material_masses': material_masses,
        'processing_data': processing_data,
        'total_material_co2': total_material_co2,
        'total_process_co2': total_process_co2,
        'overall_co2': overall_co2,
        'weighted_recycled': weighted_recycled,
        'trees_equiv': trees_equiv,
        'eol_summary': eol_summary,
        'final_summary_html': final_summary_html,
        'comparison_data': comparison_data
    }
    st.session_state.final_summary_html = final_summary_html

    # Charts
    st.markdown("## 📊 Comparison Visualizations")
    df_compare = pd.DataFrame(comparison_data)
    color_seq = ['#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = px.bar(df_compare, x="Material", y="CO2e per kg", color="Material", title="🏭 CO₂e per kg", color_discrete_sequence=color_seq)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = px.bar(df_compare, x="Material", y="Recycled Content (%)", color="Material", title="♻️ Recycled Content (%)", color_discrete_sequence=color_seq)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig = px.bar(df_compare, x="Material", y="Circularity (mapped)", color="Material", title="🔄 Circularity", color_discrete_sequence=color_seq)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5,
                          yaxis=dict(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High']))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        df_compare["Lifetime Category"] = df_compare["Lifetime (years)"].apply(lifetime_category)
        cat_map = {"Short":1, "Medium":2, "Long":3}
        df_compare["Lifetime"] = df_compare["Lifetime Category"].map(cat_map)
        fig = px.bar(df_compare, x="Material", y="Lifetime", color="Material", title="⏱️ Lifetime", color_discrete_sequence=color_seq)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5,
                          yaxis=dict(tickmode='array', tickvals=[1,2,3], ticktext=["Short","Medium","Long"]))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------
    # REPORT DOWNLOADS
    # -----------------------
    st.markdown("## 📝 Report")
    project = st.text_input("Project name", value="Sample Project")
    notes = st.text_area("Executive notes")

    summary = {
        "lifetime_years": lifetime_years,
        "overall_co2": overall_co2,
        "weighted_recycled": weighted_recycled,
        "trees_equiv": trees_equiv,
        "total_trees_equiv": total_trees_equiv,
        "eol_summary": eol_summary,
    }

    pdf_bytes = build_pdf_from_template(project, notes, summary, selected_materials, materials_dict, material_masses)
    if pdf_bytes:
        st.download_button("⬇️ Download PDF report (smart-filled)", data=pdf_bytes,
                           file_name=f"TCHAI_Report_{project.replace(' ','_')}.pdf", mime="application/pdf")
    else:
        st.warning("PDF backend not found (ReportLab). Trying DOCX fallback…")
        docx_bytes = build_docx_fallback(project, notes, summary, selected_materials, materials_dict, material_masses)
        if docx_bytes:
            st.download_button("⬇️ Download DOCX report (smart-filled)", data=docx_bytes,
                               file_name=f"TCHAI_Report_{project.replace(' ','_')}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            # Plain-text fallback
            st.warning("Neither PDF nor DOCX export is available. Providing a plain-text report.")
            lines = []
            title = f"{project} — Easy LCA Report"
            lines.append(title)
            lines.append("=" * len(title))
            lines.append("")
            lines.append("Introduction")
            lines.append("At Tchai we build different: within every brand space we design we try to leave a positive mark on people and planet.")
            lines.append("")
            lines.append("Key Metrics")
            lines.append(f"- Lifetime: {lifetime_years:.1f} years ({int(lifetime_years*52)} weeks)")
            lines.append(f"- Total CO₂e: {overall_co2:.1f} kg")
            lines.append(f"- Weighted recycled content: {weighted_recycled:.1f}%")
            lines.append(f"- Trees/year: {trees_equiv:.1f}")
            lines.append(f"- Total trees: {total_trees_equiv:.1f}")
            lines.append("")
            if notes.strip():
                lines.append("Executive Notes")
                lines.append(notes.strip())
                lines.append("")
            lines.append("Material Comparison Overview")
            lines.append("Material | CO₂e per Unit (kg) | Avg. Recycled Content | Circularity | End-of-Life | Tree Equivalent*")
            rows = _material_rows_for_report(selected_materials, materials_dict, material_masses, lifetime_years)
            for r in rows:
                lines.append(" | ".join(r))
            lines.append("")
            lines.append("*Estimated number of trees required to sequester the CO₂e emissions from one unit over the selected years.")
            lines.append("")
            lines.append("End-of-Life Summary")
            if eol_summary:
                for k, v in eol_summary.items():
                    lines.append(f"- {k}: {v}")
            else:
                lines.append("- —")
            plain_txt = "\n".join(lines).encode("utf-8")
            st.download_button("⬇️ Download Plain-Text Report",
                               data=plain_txt,
                               file_name=f"TCHAI_Report_{project.replace(' ','_')}.txt",
                               mime="text/plain")

    # Clear loaded version data so new runs don't get polluted
    if hasattr(st.session_state, 'loaded_version_data'):
        del st.session_state.loaded_version_data


# =========================
# ROUTER
# =========================
if page == "User Guide":
    user_guide_page()
else:
    assessment_page()
