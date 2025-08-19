import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
from datetime import datetime
import os
import uuid
import hashlib
from pathlib import Path
import base64

# =============================================================
# TCHAI — Easy LCA Indicator (PDF-style UI)
# - TCHAI logo in header & sidebar (auto-detected)
# - Sign-in + Create Account (local JSON; salted SHA-256)
# - Uses bundled Excel database by default (Refined database.xlsx > database.xlsx)
# - Version Management (Save/Load/Delete)
# - Visuals aligned with provided PDF
# - Downloadable HTML report + CSVs
# =============================================================

# -----------------------------
# VERSION MANAGEMENT CLASS
# -----------------------------
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

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "saved_versions" not in st.session_state:
    st.session_state.saved_versions = {}
if "final_summary_html" not in st.session_state:
    st.session_state.final_summary_html = ""
if "version_manager" not in st.session_state:
    st.session_state.version_manager = LCAVersionManager()
if "current_assessment_data" not in st.session_state:
    st.session_state.current_assessment_data = {}
if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------
# PAGE CONFIG & BRANDING
# -----------------------------
st.set_page_config(page_title="Easy LCA Indicator — TCHAI", page_icon="🌿", layout="wide")

ASSETS = Path("assets")
LOGO_PATHS = [ASSETS / "tchai_logo.png", Path("tchai_logo.png")]
logo_bytes = None
for p in LOGO_PATHS:
    if p.exists():
        logo_bytes = p.read_bytes()
        break

def logo_img_tag(height=42):
    if not logo_bytes:
        return "<span style='font-weight:800;color:#2E7D32'>TCHAI</span>"
    b64 = base64.b64encode(logo_bytes).decode("utf-8")
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

custom_css = f"""
<style>
    .stApp {{ background: linear-gradient(135deg, #F1F8E9 0%, #E8F5E8 100%); }}
    header, #MainMenu, footer {{ visibility: hidden; }}
    .primary-header {{ display:flex;align-items:center;gap:12px;justify-content:center;margin:0 0 1.2rem 0; }}
    .brand-title {{ color:#2E7D32;font-weight:800;font-size:2.2rem;letter-spacing:.5px; }}
    .version-section {{ background: linear-gradient(135deg, #E8F5E8 0%, #F1F8E9 100%); padding: 18px; border-radius: 14px; border: 3px solid #4CAF50; margin: 16px 0; box-shadow: 0 8px 25px rgba(76,175,80,.15); }}
    .info-box {{ background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%); padding: 16px; border-radius: 12px; border-left: 5px solid #2196F3; margin: 10px 0; }}
    .material-section {{ background: rgba(255,255,255,.94); padding: 22px; border-radius: 14px; border:2px solid #81C784; margin: 14px 0; box-shadow: 0 6px 18px rgba(129,199,132,.2); }}
    .summary-section {{ background: linear-gradient(135deg, #E1F5FE 0%, #F3E5F5 100%); padding: 26px; border-radius: 18px; border:3px solid #4CAF50; margin: 24px 0; box-shadow: 0 10px 28px rgba(76,175,80,.25); }}
    .metric-card {{ background: rgba(255,255,255,.96); padding: 16px; border-radius: 12px; border:2px solid #81C784; text-align:center; }}
    .chart-container {{ background: rgba(255,255,255,.95); padding: 18px; border-radius: 14px; border:2px solid #E0E0E0; margin: 14px 0; }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

cL, cM, cR = st.columns([0.14, 0.7, 0.16])
with cL:
    st.markdown(f"<div style='display:flex;justify-content:center'>{logo_img_tag(44)}</div>", unsafe_allow_html=True)
with cM:
    st.markdown("<div class='primary-header'><div class='brand-title'>🌿 Easy LCA Indicator</div></div>", unsafe_allow_html=True)
with cR:
    if st.session_state.user:
        st.markdown(f"<div style='text-align:right'>👋 <b>{st.session_state.user['full_name']}</b></div>", unsafe_allow_html=True)

# -----------------------------
# AUTH — Local demo (users.json)
# -----------------------------
USERS_FILE = Path("users.json")

def _load_users():
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except Exception:
            return {}
    return {}

def _save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))

def _hash_pw(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()

with st.sidebar:
    st.markdown('<div class="version-section">', unsafe_allow_html=True)
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px'>{logo_img_tag(40)}</div>", unsafe_allow_html=True)
    st.subheader("🔐 Sign in")

    with st.expander("How accounts work", expanded=False):
        st.markdown(
            """
            **Demo sign‑in (local only):**
            - Enter your *username* and *password*, click **Sign in**.
            - No account? Fill the fields below and click **Create account**.
            - Accounts are stored **locally** in `users.json` with a salted hash.
            - For production, we’ll switch to **Firebase/Auth0** or **streamlit‑authenticator** and add roles/password reset.
            """
        )

    username = st.text_input("Username", key="auth_user")
    password = st.text_input("Password", type="password", key="auth_pass")
    colA, colB = st.columns(2)
    if colA.button("Sign in", use_container_width=True):
        users = _load_users()
        rec = users.get(username)
        if rec and _hash_pw(password, rec.get('salt','')) == rec.get('pw_hash'):
            st.session_state.user = {"username": username, "full_name": rec.get("full_name", username)}
            st.success(f"Welcome {st.session_state.user['full_name']}!")
        else:
            st.error("Invalid credentials or user not found.")
    if colB.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.experimental_rerun()

    st.markdown("---")
    st.caption("Create a new account")
    new_user = st.text_input("New username", key="new_user")
    new_name = st.text_input("Full name (optional)", key="new_name")
    new_pw = st.text_input("New password", type="password", key="new_pw")
    if st.button("Create account", use_container_width=True):
        if not new_user or not new_pw:
            st.error("Please provide a username and password.")
        else:
            users = _load_users()
            if new_user in users:
                st.error("Username already exists.")
            else:
                salt = uuid.uuid4().hex
                users[new_user] = {"pw_hash": _hash_pw(new_pw, salt), "salt": salt, "full_name": new_name or new_user}
                _save_users(users)
                st.success("Account created. You can sign in now.")
    st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.user:
    st.info("Please sign in from the left panel to start.")
    st.stop()

# -----------------------------
# VERSION MANAGEMENT SIDEBAR
# -----------------------------
st.sidebar.markdown('<div class="version-section">', unsafe_allow_html=True)
st.sidebar.markdown("## 📁 Version Management")
version_action = st.sidebar.selectbox("Choose Action:", ["New Assessment", "Save Current", "Load Version", "Manage Versions"])

if version_action == "Save Current":
    st.sidebar.markdown("### Save Current Assessment")
    version_name = st.sidebar.text_input("Version Name:", key="save_version_name")
    version_description = st.sidebar.text_area("Description (optional):", key="save_version_desc")
    if st.sidebar.button("💾 Save Version"):
        if version_name and st.session_state.current_assessment_data:
            success, message = st.session_state.version_manager.save_version(version_name, st.session_state.current_assessment_data, version_description)
            st.sidebar.success(message) if success else st.sidebar.error(message)
        elif not version_name:
            st.sidebar.error("Please enter a version name")
        else:
            st.sidebar.error("No assessment data to save. Complete an assessment first.")
elif version_action == "Load Version":
    st.sidebar.markdown("### Load Saved Version")
    versions = st.session_state.version_manager.list_versions()
    if versions:
        version_options = list(versions.keys())
        selected_version = st.sidebar.selectbox("Select Version:", version_options)
        if selected_version:
            info = versions[selected_version]
            st.sidebar.write(f"**Description:** {info.get('description', 'No description')}")
            st.sidebar.write(f"**Created:** {info.get('created_at', 'Unknown')}")
            st.sidebar.write(f"**Materials:** {info.get('materials_count', 0)}")
            st.sidebar.write(f"**Total CO₂:** {info.get('total_co2', 0):.2f} kg")
            if st.sidebar.button("📂 Load Version"):
                data, message = st.session_state.version_manager.load_version(selected_version)
                if data:
                    st.session_state.loaded_version_data = data
                    st.sidebar.success(message)
                    st.sidebar.info("Data loaded! Values will prefill where possible.")
                else:
                    st.sidebar.error(message)
    else:
        st.sidebar.info("No saved versions available")
elif version_action == "Manage Versions":
    st.sidebar.markdown("### Manage Versions")
    versions = st.session_state.version_manager.list_versions()
    if versions:
        version_to_delete = st.sidebar.selectbox("Select Version to Delete:", list(versions.keys()))
        if st.sidebar.button("🗑️ Delete Version", type="secondary"):
            success, message = st.session_state.version_manager.delete_version(version_to_delete)
            st.sidebar.success(message) if success else st.sidebar.error(message)
            if success:
                st.experimental_rerun()
        st.sidebar.markdown("### Version List")
        for name, info in versions.items():
            st.sidebar.write(f"**{name}**")
            st.sidebar.write(f"  📅 {info.get('created_at', 'Unknown')[:10]}")
            st.sidebar.write(f"  📊 {info.get('materials_count', 0)} materials")
            st.sidebar.write("---")
    else:
        st.sidebar.info("No versions to manage")

st.sidebar.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# QUICK INSTRUCTIONS (aligned with your doc)
# -----------------------------
with st.expander("📘 Quick Instructions", expanded=True):
    st.markdown(
        """
        1) **Upload your Excel database** (or let the app use the bundled one).
        2) **Enter the lifetime** of the final product in **weeks**.
        3) **Select materials** and enter **mass (kg)**.
        4) **Add processing steps** for each material (process + amount).
        5) Review the **Final Summary** and **End‑of‑Life**.
        6) **Save** your assessment as a **Version** (left panel) and **Download** a report.
        """
    )

# -----------------------------
# GLOBAL INPUTS & HELPERS
# -----------------------------
def extract_number(value):
    try:
        return float(value)
    except Exception:
        s = str(value).replace(',', '.')
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def lifetime_category(v):
    v = extract_number(v)
    if v < 5: return "Short"
    if v <= 15: return "Medium"
    return "Long"

# Default database fallback chain
DB_CANDIDATES = [Path("Refined database.xlsx"), Path("database.xlsx")]

st.markdown("""
<div class="info-box">
  <h3 style="margin:0;color:#1976D2;">📂 Upload Your Excel Database</h3>
  <p style="margin:0">Expected sheets: <b>Materials</b> and <b>Processes</b>. If you skip upload, we'll use a bundled Excel if found.</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Excel Database", type=["xlsx"])
using_bundled = False
if not uploaded_file:
    for p in DB_CANDIDATES:
        if p.exists():
            uploaded_file = p.open("rb")
            using_bundled = True
            break
    if not uploaded_file:
        st.info("👆 Please upload your Excel database file to continue.")
        st.stop()

xls = pd.ExcelFile(uploaded_file)

def extract_material_data(sheet_df: pd.DataFrame):
    sheet_df.columns = [str(c).strip() for c in sheet_df.columns]
    expected = ["Material name","CO2e (kg)","Recycled Content","EoL","Lifetime","Comment","Circularity","Alternative Material"]
    for col in expected:
        if col not in sheet_df.columns:
            st.error(f"Missing column in Materials: '{col}'")
            return {}
    out = {}
    for _, r in sheet_df.iterrows():
        name = str(r["Material name"]).strip() if pd.notna(r["Material name"]) else ""
        if not name:
            continue
        out[name] = {
            "CO₂e (kg)": extract_number(r["CO2e (kg)"]),
            "Recycled Content": extract_number(r["Recycled Content"]),
            "EoL": str(r["EoL"]).strip() if pd.notna(r["EoL"]) else "Unknown",
            "Lifetime": str(r["Lifetime"]).strip() if pd.notna(r["Lifetime"]) else "Unknown",
            "Comment": str(r["Comment"]).strip() if pd.notna(r["Comment"]) and str(r["Comment"]).strip() else "No comment",
            "Circularity": str(r["Circularity"]).strip() if pd.notna(r["Circularity"]) else "Unknown",
            "Alternative Material": str(r["Alternative Material"]).strip() if pd.notna(r["Alternative Material"]) else "None",
        }
    return out

def extract_processes_data(sheet_df: pd.DataFrame):
    sheet_df.columns = [str(c).strip().replace("₂","2").replace("CO₂","CO2") for c in sheet_df.columns]
    proc_col = next((c for c in sheet_df.columns if 'process' in c.lower()), None)
    co2_col = next((c for c in sheet_df.columns if 'co2' in c.lower()), None)
    unit_col = next((c for c in sheet_df.columns if 'unit' in c.lower()), None)
    if not proc_col or not co2_col or not unit_col:
        st.error("Could not detect column names in 'Processes' — please check Excel.")
        return {}
    out = {}
    for _, r in sheet_df.iterrows():
        pname = str(r[proc_col]).strip() if pd.notna(r[proc_col]) else ""
        if not pname:
            continue
        out[pname] = {"CO₂e": extract_number(r[co2_col]), "Unit": str(r[unit_col]).strip() if pd.notna(r[unit_col]) else "Unknown"}
    return out

materials_dict = extract_material_data(pd.read_excel(xls, sheet_name="Materials"))
processes_dict = extract_processes_data(pd.read_excel(xls, sheet_name="Processes"))

if using_bundled:
    st.success("Using bundled Excel database.")

# Lifetime (weeks) with version prefill
default_lifetime = 52
if hasattr(st.session_state, 'loaded_version_data') and 'lifetime_weeks' in st.session_state.loaded_version_data:
    default_lifetime = st.session_state.loaded_version_data['lifetime_weeks']

lifetime_weeks = st.number_input("Enter the lifetime of the final product (in weeks):", min_value=1, value=default_lifetime, key="lifetime_weeks")
lifetime_years = lifetime_weeks / 52

# -----------------------------
# MATERIALS & PROCESSES (PDF-like blocks)
# -----------------------------
# Prefill selection if version loaded
default_selected = []
if hasattr(st.session_state, 'loaded_version_data') and 'selected_materials' in st.session_state.loaded_version_data:
    default_selected = st.session_state.loaded_version_data['selected_materials']

selected_materials = st.multiselect("Select Materials", options=list(materials_dict.keys()), default=default_selected)
if not selected_materials:
    st.info("Please select at least one material.")
    st.stop()

# Accumulators
total_material_co2 = 0.0
total_process_co2 = 0.0
total_mass = 0.0
total_weighted_recycled = 0.0
eol_summary = {}
comparison_data = []
material_masses = {}
processing_data = {}

circularity_map = {"High":3, "Medium":2, "Low":1, "Not Circular":0}

for material_name in selected_materials:
    st.markdown('<div class="material-section">', unsafe_allow_html=True)
    st.header(f"🔧 Material: {material_name}")
    m = materials_dict[material_name]

    # Prefill mass
    default_mass = 1.0
    if hasattr(st.session_state, 'loaded_version_data') and 'material_masses' in st.session_state.loaded_version_data and material_name in st.session_state.loaded_version_data['material_masses']:
        default_mass = st.session_state.loaded_version_data['material_masses'][material_name]

    mass = st.number_input(f"Enter mass of {material_name} (kg)", min_value=0.0, value=default_mass, key=f"mass_{material_name}")
    material_masses[material_name] = mass

    total_mass += mass
    mat_co2 = mass * m["CO₂e (kg)"]
    total_material_co2 += mat_co2
    total_weighted_recycled += mass * m["Recycled Content"]

    st.write(f"**CO₂e per kg:** {m['CO₂e (kg)']} kg")
    st.write(f"**Recycled Content:** {m['Recycled Content']}%")
    st.write(f"**Lifetime:** {m['Lifetime']}")
    st.write(f"**Circularity:** {m['Circularity']}")
    st.write(f"**Comment:** {m['Comment']}")
    st.write(f"**Alternative Material:** {m['Alternative Material']}")

    eol_summary[material_name] = m["EoL"]

    # Processing steps
    default_steps = 0
    if hasattr(st.session_state, 'loaded_version_data') and 'processing_data' in st.session_state.loaded_version_data and material_name in st.session_state.loaded_version_data['processing_data']:
        default_steps = len(st.session_state.loaded_version_data['processing_data'][material_name])

    n_proc = int(st.number_input(f"How many processing steps for {material_name}?", min_value=0, max_value=10, value=default_steps, key=f"proc_steps_{material_name}"))

    proc_total = 0.0
    processing_data[material_name] = []

    for i in range(n_proc):
        default_process = ""
        default_amount = 1.0
        if hasattr(st.session_state, 'loaded_version_data') and 'processing_data' in st.session_state.loaded_version_data and material_name in st.session_state.loaded_version_data['processing_data'] and i < len(st.session_state.loaded_version_data['processing_data'][material_name]):
            rec = st.session_state.loaded_version_data['processing_data'][material_name][i]
            default_process = rec.get('process', "")
            default_amount = rec.get('amount', 1.0)
        proc_selected = st.selectbox(f"Process #{i+1} for {material_name}", options=[""] + list(processes_dict.keys()), index=0 if default_process=="" else (list(processes_dict.keys()).index(default_process)+1 if default_process in processes_dict else 0), key=f"process_{material_name}_{i}")
        if proc_selected:
            props = processes_dict.get(proc_selected, {})
            co2e_per_unit = props.get("CO₂e", 0)
            unit = props.get("Unit", "Unknown")
            amount_processed = st.number_input(f"Enter amount for '{proc_selected}' ({unit})", min_value=0.0, value=default_amount, key=f"amount_{material_name}_{i}")
            proc_total += amount_processed * co2e_per_unit
            processing_data[material_name].append({'process': proc_selected,'amount': amount_processed,'co2e_per_unit': co2e_per_unit,'unit': unit})

    total_process_co2 += proc_total

    circ_val = circularity_map.get(m["Circularity"].title(), 0)
    lifetime_numeric = extract_number(m["Lifetime"])
    comparison_data.append({
        "Material": material_name,
        "CO2e per kg": m["CO₂e (kg)"],
        "Recycled Content (%)": m["Recycled Content"],
        "Circularity (mapped)": circ_val,
        "Circularity (text)": m["Circularity"],
        "Lifetime (years)": lifetime_numeric,
        "Lifetime (text)": m["Lifetime"]
    })

    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# FINAL SUMMARY (matching PDF)
# -----------------------------
overall_co2 = total_material_co2 + total_process_co2
weighted_recycled = (total_weighted_recycled / total_mass) if total_mass > 0 else 0

total_trees_equiv = overall_co2 / 22
lifetime_years = lifetime_years if lifetime_years > 0 else 1
trees_equiv = overall_co2 / (22 * lifetime_years)

final_summary_html = f"""
<div class='summary-section'>
  <h2 style='text-align:center;'>🌍 Final Summary</h2>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;">
    <div class='metric-card'><h3>♻️ Weighted Recycled Content</h3><p style='color:#4CAF50'>{weighted_recycled:.1f}%</p></div>
    <div class='metric-card'><h3>🏭 Total CO₂ Impact (Materials)</h3><p style='color:#4CAF50'>{total_material_co2:.1f} kg</p></div>
    <div class='metric-card'><h3>🔧 Total CO₂ Impact (Processes)</h3><p style='color:#4CAF50'>{total_process_co2:.1f} kg</p></div>
    <div class='metric-card'><h3>🌍 Total Impact CO₂e per kg</h3><p style='color:#D32F2F'>{overall_co2:.1f} kg</p></div>
    <div class='metric-card'><h3>🌳 Tree Equivalent</h3><p>{trees_equiv:.1f} trees/year over {lifetime_years:.1f} years</p></div>
    <div class='metric-card'><h3>Total Tree Equivalent 🌳</h3><p>{total_trees_equiv:.1f} trees</p></div>
  </div>
  <h3 style='text-align:center;margin-top:20px;'>🔄 End-of-Life Summary</h3>
  <div style='background:rgba(255,255,255,0.7);padding:12px;border-radius:10px;'>
    <ul style='list-style:none;padding:0;margin:0;'>
"""
for material, eol in eol_summary.items():
    final_summary_html += f"<li style='padding:8px;margin:6px 0;background:rgba(76,175,80,0.1);border-left:4px solid #4CAF50;border-radius:6px'><strong>{material}</strong>: {eol}</li>"
final_summary_html += """
    </ul>
  </div>
</div>
"""

st.markdown(final_summary_html, unsafe_allow_html=True)

# Store assessment for versioning
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
    'comparison_data': comparison_data,
}

# -----------------------------
# COMPARISON VISUALS (PDF style)
# -----------------------------
st.markdown("## 📊 Comparison Visualizations")

df_compare = pd.DataFrame(comparison_data)
palette = ['#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig1 = px.bar(df_compare, x="Material", y="CO2e per kg", color="Material", title="🏭 CO₂e per kg Comparison", color_discrete_sequence=palette)
    fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5)
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig2 = px.bar(df_compare, x="Material", y="Recycled Content (%)", color="Material", title="♻️ Recycled Content Comparison", color_discrete_sequence=palette)
    fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    fig3 = px.bar(df_compare, x="Material", y="Circularity (mapped)", color="Material", title="🔄 Circularity Comparison", color_discrete_sequence=palette)
    fig3.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5, yaxis=dict(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High']))
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    df_compare["Lifetime Category"] = df_compare["Lifetime (years)"].apply(lifetime_category)
    lifetime_map = {"Short":1, "Medium":2, "Long":3}
    df_compare["Lifetime"] = df_compare["Lifetime Category"].map(lifetime_map)
    fig4 = px.bar(df_compare, x="Material", y="Lifetime", color="Material", title="⏱️ Lifetime Comparison", color_discrete_sequence=palette)
    fig4.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', title_x=0.5, yaxis=dict(tickmode='array', tickvals=[1,2,3], ticktext=["Short","Medium","Long"]))
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------
# REPORT DOWNLOADS
# -----------------------------
st.markdown("### 🧾 Report")
project_name = st.text_input("Project name", value="Sample Project")
notes = st.text_area("Executive notes (optional)")

logo_tag = logo_img_tag(44)
report_html = f"""
<!doctype html>
<html><head><meta charset='utf-8'>
<title>LCA Report — {project_name}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 24px; }}
  header {{ display:flex; align-items:center; gap:12px; margin-bottom: 12px; }}
  .title {{ color:#2E7D32; font-size:20px; font-weight:800; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border:1px solid #e5e7eb; padding:6px 8px; text-align:left; }}
  .badge {{ display:inline-block; background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:999px; font-weight:700; }}
  .note {{ background:#f8fafc; padding:12px; border-radius:8px; }}
</style></head>
<body>
  <header>{logo_tag}<div class='title'>TCHAI — Easy LCA Indicator</div></header>
  <div><strong>Project:</strong> {project_name}</div>
  <div style='margin:6px 0'><span class='badge'>Total Emissions: {overall_co2:.2f} kg CO₂e</span></div>
  <h3>Final Summary</h3>
  {final_summary_html}
  <h3>Notes</h3>
  <div class='note'>{notes or '—'}</div>
</body></html>
"""

st.download_button("⬇️ Download HTML report", data=report_html.encode("utf-8"), file_name=f"LCA_Report_{project_name.replace(' ','_')}.html", mime="text/html")

# CSV exports
if comparison_data:
    csv_compare = pd.DataFrame(comparison_data).to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV — Comparison", data=csv_compare, file_name=f"LCA_Comparison_{project_name.replace(' ','_')}.csv", mime="text/csv")

    summary_df = pd.DataFrame({
        'Metric': ['Weighted Recycled %','Total CO2 (materials)','Total CO2 (processes)','Overall CO2','Trees/year','Total trees'],
        'Value': [weighted_recycled, total_material_co2, total_process_co2, overall_co2, trees_equiv, total_trees_equiv]
    })
    st.download_button("⬇️ Download CSV — Summary", data=summary_df.to_csv(index=False).encode("utf-8"), file_name=f"LCA_Summary_{project_name.replace(' ','_')}.csv", mime="text/csv")

# -----------------------------
# CLEAR LOADED VERSION (optional)
# -----------------------------
if hasattr(st.session_state, 'loaded_version_data'):
    del st.session_state.loaded_version_data
