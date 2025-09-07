import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
from datetime import datetime
import os
from io import BytesIO

# ------------------------------------------------------------------
# VERSION MANAGEMENT CLASS 
# ------------------------------------------------------------------
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
        """Save complete LCA assessment data"""
        metadata = self._load_metadata()
        
        if version_name in metadata:
            return False, f"Version '{version_name}' already exists!"
        
        # Create version data structure
        version_data = {
            'assessment_data': assessment_data,
            'timestamp': datetime.now().isoformat(),
            'description': description
        }
        
        # Save to file
        filename = f"{version_name}.json"
        filepath = os.path.join(self.storage_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(version_data, f)
        
        # Update metadata
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
        """Load LCA assessment data"""
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
        """List all available versions"""
        metadata = self._load_metadata()
        return metadata
    
    def delete_version(self, version_name):
        """Delete a version"""
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

# ------------------------------------------------------------------
# SESSION-STATE INITIALIZATION for Versioning and App Data
# ------------------------------------------------------------------
if "saved_versions" not in st.session_state:
    st.session_state.saved_versions = {}
if "final_summary_html" not in st.session_state:
    st.session_state.final_summary_html = ""
if "version_manager" not in st.session_state:
    st.session_state.version_manager = LCAVersionManager()
if "current_assessment_data" not in st.session_state:
    st.session_state.current_assessment_data = {}
if "comparison_data" not in st.session_state:
    st.session_state.comparison_data = []
if "uploaded_excel" not in st.session_state:
    st.session_state.uploaded_excel = None

# ------------------------------------------------------------------
# PAGE CONFIGURATION & CUSTOM CSS
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Easy LCA Indicator",
    page_icon="🌿",
    layout="wide"
)

custom_css = """
<style>
    .stApp { background: linear-gradient(135deg, #F1F8E9 0%, #E8F5E8 100%); }
    .primary-header { color:#2E7D32 !important; text-align:center; font-size:3rem !important; font-weight:700 !important; margin-bottom:1rem !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .chart-container { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 15px; margin: 20px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.1); border: 2px solid #E0E0E0; }
    .material-section { background: rgba(255,255,255,0.9); padding: 25px; border-radius: 15px; margin: 20px 0; border: 2px solid #81C784; box-shadow: 0 6px 20px rgba(129,199,132,0.2); }
    .info-box { background: linear-gradient(135deg,#E3F2FD 0%,#BBDEFB 100%); padding:20px; border-radius:12px; border-left:5px solid #2196F3; margin:15px 0; box-shadow:0 4px 12px rgba(33,150,243,0.15); }
    .summary-section { background: linear-gradient(135deg,#E1F5FE 0%,#F3E5F5 100%); padding: 30px; border-radius: 20px; margin: 30px 0; border: 3px solid #4CAF50; box-shadow: 0 10px 30px rgba(76,175,80,0.25); }
    .metric-card { background: rgba(255,255,255,0.95); padding:20px; border-radius:12px; border:2px solid #81C784; margin:10px; text-align:center; box-shadow:0 6px 18px rgba(129,199,132,0.2); }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<h1 class="primary-header">🌿 Easy LCA Indicator</h1>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# SIDEBAR NAVIGATION (Radio Buttons) — includes a dedicated Versions page
# ------------------------------------------------------------------
nav = st.sidebar.radio(
    "Navigate",
    [
        "Inputs",
        "Results & Comparison",
        "Final Summary",
        "Report",
        "📁 Versions",
    ],
    index=0,
)

# ------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------
def extract_number(value):
    try:
        return float(value)
    except Exception:
        s = str(value).replace(',', '.')
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0


def extract_material_data(sheet_df):
    sheet_df.columns = [str(c).strip() for c in sheet_df.columns]
    expected = [
        "Material name", "CO2e (kg)", "Recycled Content", "EoL",
        "Lifetime", "Comment", "Circularity", "Alternative Material"
    ]
    for col in expected:
        if col not in sheet_df.columns:
            st.error(f"Missing column in Materials sheet: '{col}'")
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
            "Comment": str(row["Comment"]).strip() if pd.notna(row["Comment"]) else "",
            "Circularity": str(row["Circularity"]).strip() if pd.notna(row["Circularity"]) else "Unknown",
            "Alternative Material": str(row["Alternative Material"]).strip() if pd.notna(row["Alternative Material"]) else "None",
        }
    return out


def extract_processes_data(sheet_df):
    sheet_df.columns = [str(c).strip().replace("₂", "2").replace("CO₂", "CO2") for c in sheet_df.columns]
    proc_col = next((c for c in sheet_df.columns if 'process' in c.lower()), None)
    co2_col = next((c for c in sheet_df.columns if 'co2' in c.lower()), None)
    unit_col = next((c for c in sheet_df.columns if 'unit' in c.lower()), None)
    if not proc_col or not co2_col or not unit_col:
        st.error("Could not detect correct column names in 'Processes' sheet. Expected names containing 'process', 'co2', 'unit'.")
        return {}
    out = {}
    for _, row in sheet_df.iterrows():
        pname = str(row[proc_col]).strip() if pd.notna(row[proc_col]) else ""
        if not pname:
            continue
        out[pname] = {
            "CO₂e": extract_number(row[co2_col]),
            "Unit": str(row[unit_col]).strip() if pd.notna(row[unit_col]) else "Unknown",
        }
    return out


def compute_assessment(materials_dict, processes_dict, selected_materials, lifetime_weeks, prior_processing=None, prior_masses=None):
    circularity_mapping = {"High": 3, "Medium": 2, "Low": 1, "Not Circular": 0}

    total_material_co2 = 0.0
    total_process_co2 = 0.0
    total_mass = 0.0
    total_weighted_recycled = 0.0
    eol_summary = {}
    comparison_data = []
    material_masses = {}
    processing_data = {}

    lifetime_years = lifetime_weeks / 52.0 if lifetime_weeks else 1.0

    for material_name in selected_materials:
        mat = materials_dict[material_name]
        default_mass = (prior_masses or {}).get(material_name, 1.0)
        mass = st.number_input(f"Enter mass of {material_name} (kg)", min_value=0.0, value=float(default_mass), key=f"mass_{material_name}")
        material_masses[material_name] = mass
        total_mass += mass
        total_material_co2 += mass * mat["CO₂e (kg)"]
        total_weighted_recycled += mass * mat["Recycled Content"]
        eol_summary[material_name] = mat["EoL"]

        # Processing steps
        loaded_list = (prior_processing or {}).get(material_name, [])
        default_steps = len(loaded_list)
        n_proc = int(st.number_input(f"How many processing steps for {material_name}?", min_value=0, max_value=10, value=default_steps, key=f"proc_steps_{material_name}"))
        proc_total = 0.0
        processing_data[material_name] = []
        for i in range(n_proc):
            default_process = loaded_list[i]['process'] if i < len(loaded_list) else ""
            default_amount = float(loaded_list[i]['amount']) if i < len(loaded_list) else 1.0
            proc_selected = st.selectbox(
                f"Process #{i+1} for {material_name}", options=[""] + list(processes_dict.keys()),
                index=0 if default_process == "" else (list(processes_dict.keys()).index(default_process) + 1 if default_process in processes_dict else 0),
                key=f"process_{material_name}_{i}"
            )
            if proc_selected:
                props = processes_dict.get(proc_selected, {})
                co2e_per_unit = props.get("CO₂e", 0)
                unit = props.get("Unit", "Unknown")
                amount_processed = st.number_input(f"Enter amount for '{proc_selected}' ({unit})", min_value=0.0, value=default_amount, key=f"amount_{material_name}_{i}")
                proc_total += amount_processed * co2e_per_unit
                processing_data[material_name].append({
                    'process': proc_selected, 'amount': amount_processed, 'co2e_per_unit': co2e_per_unit, 'unit': unit
                })
        total_process_co2 += proc_total

        circ_value = circularity_mapping.get(mat["Circularity"].title(), 0)
        lifetime_numeric = extract_number(mat["Lifetime"])
        comparison_data.append({
            "Material": material_name,
            "CO2e per kg": mat["CO₂e (kg)"],
            "Recycled Content (%)": mat["Recycled Content"],
            "Circularity (mapped)": circ_value,
            "Circularity (text)": mat["Circularity"],
            "Lifetime (years)": lifetime_numeric,
            "Lifetime (text)": mat["Lifetime"]
        })

        with st.expander(f"Details — {material_name}", expanded=False):
            st.write(f"**CO₂e per kg:** {mat['CO₂e (kg)']} kg")
            st.write(f"**Recycled Content:** {mat['Recycled Content']}%")
            st.write(f"**Lifetime:** {mat['Lifetime']}")
            st.write(f"**Circularity:** {mat['Circularity']}")
            if mat.get("Comment"): st.write(f"**Comment:** {mat['Comment']}")
            st.write(f"**Alternative Material:** {mat['Alternative Material']}")

    overall_co2 = total_material_co2 + total_process_co2
    trees_equiv_total = overall_co2 / 22
    trees_equiv_year = overall_co2 / (22 * max(lifetime_years, 1e-9))
    weighted_recycled = (total_weighted_recycled / total_mass) if total_mass > 0 else 0

    # Persist in session state
    st.session_state.current_assessment_data = {
        'lifetime_weeks': lifetime_weeks,
        'selected_materials': selected_materials,
        'material_masses': material_masses,
        'processing_data': processing_data,
        'total_material_co2': total_material_co2,
        'total_process_co2': total_process_co2,
        'overall_co2': overall_co2,
        'weighted_recycled': weighted_recycled,
        'trees_equiv': trees_equiv_year,
        'trees_equiv_total': trees_equiv_total,
        'comparison_data': comparison_data
    }

    return {
        'overall_co2': overall_co2,
        'total_material_co2': total_material_co2,
        'total_process_co2': total_process_co2,
        'weighted_recycled': weighted_recycled,
        'trees_equiv_year': trees_equiv_year,
        'trees_equiv_total': trees_equiv_total,
        'comparison_data': comparison_data,
        'eol_summary': eol_summary
    }


def lifetime_category(v):
    try:
        v = float(v)
    except Exception:
        return "Medium"
    if v < 5:
        return "Short"
    elif v <= 15:
        return "Medium"
    else:
        return "Long"

# ------------------------------------------------------------------
# PAGE: 📁 Versions (moved out of any workspace page)
# ------------------------------------------------------------------
if nav == "📁 Versions":
    st.subheader("📁 Version Management")

    colA, colB, colC = st.columns([1,1,1])

    with colA:
        st.markdown("### 💾 Save Current")
        vname = st.text_input("Version Name:", key="save_version_name")
        vdesc = st.text_area("Description (optional):", key="save_version_desc")
        if st.button("Save Version"):
            if vname and st.session_state.current_assessment_data:
                success, msg = st.session_state.version_manager.save_version(vname, st.session_state.current_assessment_data, vdesc)
                st.success(msg) if success else st.error(msg)
            elif not vname:
                st.error("Please enter a version name")
            else:
                st.error("No assessment data to save. Complete an assessment first on the Inputs page.")

    with colB:
        st.markdown("### 📂 Load Version")
        versions = st.session_state.version_manager.list_versions()
        if versions:
            options = list(versions.keys())
            selected = st.selectbox("Select Version", options)
            if selected:
                info = versions[selected]
                st.caption(f"**Created:** {info.get('created_at','')}")
                st.caption(f"**Materials:** {info.get('materials_count',0)}")
                st.caption(f"**Total CO₂:** {info.get('total_co2',0):.2f} kg")
                if st.button("Load Selected"):
                    data, msg = st.session_state.version_manager.load_version(selected)
                    if data:
                        # load into session so it will prefill Inputs page controls
                        st.session_state.loaded_version_data = data
                        st.success(msg)
                        st.info("Go to the Inputs page — loaded values will appear as defaults.")
                    else:
                        st.error(msg)
        else:
            st.info("No saved versions available yet.")

    with colC:
        st.markdown("### 🗑️ Manage Versions")
        versions = st.session_state.version_manager.list_versions()
        if versions:
            to_delete = st.selectbox("Select Version to Delete", list(versions.keys()), key="del_ver")
            if st.button("Delete Version"):
                ok, msg = st.session_state.version_manager.delete_version(to_delete)
                if ok:
                    st.success(msg)
                    st.experimental_rerun()
                else:
                    st.error(msg)
        else:
            st.info("Nothing to manage yet.")

    st.markdown("---")
    st.markdown("#### New Assessment")
    if st.button("Start New Assessment"):
        for k in [
            'current_assessment_data','comparison_data','final_summary_html',
            'loaded_version_data','uploaded_excel']:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Cleared current data. Go to Inputs to begin.")

# ------------------------------------------------------------------
# PAGE: Inputs — upload Excel, choose materials/processes, compute
# ------------------------------------------------------------------
if nav == "Inputs":
    st.markdown("""
    <div class="info-box">
        <h3 style="margin-top:0;color:#1976D2;">📂 Upload Your Excel Database</h3>
        <p style="margin-bottom:0;">Upload your Excel file containing <b>Materials</b> and <b>Processes</b> sheets to begin.</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload Excel Database", type=["xlsx"], key="uploader")
    if uploaded is not None:
        st.session_state.uploaded_excel = uploaded.getvalue()

    if st.session_state.uploaded_excel is None:
        st.info("👆 Please upload your Excel database to continue.")
        st.stop()

    xls = pd.ExcelFile(BytesIO(st.session_state.uploaded_excel))
    df_materials = pd.read_excel(xls, sheet_name="Materials")
    materials_dict = extract_material_data(df_materials)
    df_processes = pd.read_excel(xls, sheet_name="Processes")
    processes_dict = extract_processes_data(df_processes)

    # Global lifetime
    default_life = 52
    if hasattr(st.session_state, 'loaded_version_data') and 'lifetime_weeks' in st.session_state.loaded_version_data:
        default_life = int(st.session_state.loaded_version_data['lifetime_weeks'])
    lifetime_weeks = st.number_input("Enter the lifetime of the final product (in weeks):", min_value=1, value=default_life, key="lifetime_weeks")

    # Materials selection
    default_materials = []
    if hasattr(st.session_state, 'loaded_version_data') and 'selected_materials' in st.session_state.loaded_version_data:
        default_materials = st.session_state.loaded_version_data['selected_materials']

    selected_materials = st.multiselect("Select Materials", options=list(materials_dict.keys()), default=default_materials)
    if not selected_materials:
        st.info("Please select at least one material.")
        st.stop()

    # Prior masses & processing for defaults
    prior_masses = None
    prior_processing = None
    if hasattr(st.session_state, 'loaded_version_data'):
        prior_masses = st.session_state.loaded_version_data.get('material_masses')
        prior_processing = st.session_state.loaded_version_data.get('processing_data')

    # Compute assessment with interactive inputs
    compute_assessment(materials_dict, processes_dict, selected_materials, lifetime_weeks, prior_processing, prior_masses)

# ------------------------------------------------------------------
# PAGE: Results & Comparison — charts
# ------------------------------------------------------------------
if nav == "Results & Comparison":
    data = st.session_state.get('current_assessment_data', {})
    comp = data.get('comparison_data', [])
    if not comp:
        st.info("No results yet. Go to Inputs and complete an assessment.")
        st.stop()

    st.markdown("## 📊 Comparison Visualizations")
    df_compare = pd.DataFrame(comp)
    my_colors = ['#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig_co2 = px.bar(df_compare, x="Material", y="CO2e per kg", color="Material", title="🏭 CO₂e per kg Comparison", color_discrete_sequence=my_colors)
        fig_co2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2E7D32'), title_font_size=18, title_x=0.5)
        st.plotly_chart(fig_co2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig_r = px.bar(df_compare, x="Material", y="Recycled Content (%)", color="Material", title="♻️ Recycled Content Comparison", color_discrete_sequence=my_colors)
        fig_r.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2E7D32'), title_font_size=18, title_x=0.5)
        st.plotly_chart(fig_r, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        fig_c = px.bar(df_compare, x="Material", y="Circularity (mapped)", color="Material", title="🔄 Circularity Comparison", color_discrete_sequence=my_colors)
        fig_c.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2E7D32'), title_font_size=18, title_x=0.5,
                            yaxis=dict(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High']))
        st.plotly_chart(fig_c, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        df_compare = df_compare.copy()
        df_compare["Lifetime Category"] = df_compare["Lifetime (years)"].apply(lifetime_category)
        lifetime_map = {"Short": 1, "Medium": 2, "Long": 3}
        df_compare["Lifetime"] = df_compare["Lifetime Category"].map(lifetime_map)
        fig_l = px.bar(df_compare, x="Material", y="Lifetime", color="Material", title="⏱️ Lifetime Comparison", color_discrete_sequence=my_colors)
        fig_l.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#2E7D32'), title_font_size=18, title_x=0.5,
                            yaxis=dict(tickmode='array', tickvals=[1,2,3], ticktext=['Short','Medium','Long']))
        st.plotly_chart(fig_l, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# PAGE: Final Summary — pretty snapshot assembled from session data
# ------------------------------------------------------------------
if nav == "Final Summary":
    data = st.session_state.get('current_assessment_data', {})
    if not data:
        st.info("No assessment yet. Go to Inputs first.")
        st.stop()

    weighted_recycled = data.get('weighted_recycled', 0)
    tot_mat = data.get('total_material_co2', 0)
    tot_proc = data.get('total_process_co2', 0)
    overall = data.get('overall_co2', 0)
    trees_per_year = data.get('trees_equiv', 0)
    trees_total = data.get('trees_equiv_total', 0)
    lifetime_weeks = data.get('lifetime_weeks', 52)
    lifetime_years = lifetime_weeks/52

    html = f"""
    <div class="summary-section">
      <h2>🌍 Final Summary</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin:20px 0;">
        <div class="metric-card"><h3 style='color:#2E7D32;margin:0;'>♻️ Weighted Recycled Content</h3><p style='font-size:0.9rem;color:#4CAF50;'>{weighted_recycled:.1f}%</p></div>
        <div class="metric-card"><h3 style='color:#2E7D32;margin:0;'>🏭 Total CO₂ Impact (Materials)</h3><p style='font-size:0.9rem;color:#4CAF50;'>{tot_mat:.1f} kg</p></div>
        <div class="metric-card"><h3 style='color:#2E7D32;margin:0;'>🔧 Total CO₂ Impact (Processes)</h3><p style='font-size:0.9rem;color:#4CAF50;'>{tot_proc:.1f} kg</p></div>
        <div class="metric-card"><h3 style='color:#2E7D32;margin:0;'>🌍 Total Impact CO₂e</h3><p style='font-size:0.9rem;color:#D32F2F;'>{overall:.1f} kg</p></div>
        <div class="metric-card"><h3 style='color:#2E7D32;margin:0;'>🌳 Tree Equivalent (per year)</h3><p style='font-size:0.9rem;color:#2E7D32;'>{trees_per_year:.1f} trees/year over {lifetime_years:.1f} years</p></div>
        <div class="metric-card"><h3 style='color:#2E7D32;margin:0;'>Total Tree Equivalent</h3><p style='font-size:0.9rem;color:#2E7D32;'>{trees_total:.1f} trees</p></div>
      </div>
    </div>
    """
    st.session_state.final_summary_html = html
    st.markdown(html, unsafe_allow_html=True)

# ------------------------------------------------------------------
# PAGE: Report — placeholder (export could be wired to ReportLab/python-docx)
# ------------------------------------------------------------------
if nav == "Report":
    if not st.session_state.get('current_assessment_data'):
        st.info("No assessment yet. Go to Inputs first.")
        st.stop()
    st.subheader("🧾 Report Export")
    st.write("PDF/DOCX export can be added here (ReportLab/python-docx). For now, you can copy the Final Summary and paste into your template.")
