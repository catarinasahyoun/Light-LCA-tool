import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
from datetime import datetime
import os


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
# SESSION-STATE INITIALIZATION for Versioning and Other Data
# ------------------------------------------------------------------
if "saved_versions" not in st.session_state:
    st.session_state.saved_versions = {}
if "final_summary_html" not in st.session_state:
    st.session_state.final_summary_html = ""
if "version_manager" not in st.session_state:
    st.session_state.version_manager = LCAVersionManager()
if "current_assessment_data" not in st.session_state:
    st.session_state.current_assessment_data = {}

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
    /* Main app styling */
    .stApp {
        background: linear-gradient(135deg, #F1F8E9 0%, #E8F5E8 100%);
    }
    
    /* Header styling */
    .primary-header {
        color: #2E7D32 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        text-align: center;
        font-size: 3rem !important;
        font-weight: 700 !important;
        margin-bottom: 2rem !important;
        text-shadow: 2px 2px 4px rgba(46, 125, 50, 0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #2E7D32 0%, #388E3C 100%) !important;
    }
    
    /* Sidebar text color */
    .css-1d391kg .element-container {
        color: white !important;
    }
    
    /* Version section styling */
    .version-section {
        background: linear-gradient(135deg, #E8F5E8 0%, #F1F8E9 100%);
        padding: 25px;
        border-radius: 15px;
        border: 3px solid #4CAF50;
        margin: 20px 0;
        box-shadow: 0 8px 25px rgba(76, 175, 80, 0.15);
        backdrop-filter: blur(10px);
    }
    
    /* Success message styling */
    .version-success {
        background: linear-gradient(135deg, #DFF2BF 0%, #C8E6C8 100%);
        color: #2E7D32;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #4CAF50;
        box-shadow: 0 4px 15px rgba(79, 138, 16, 0.2);
        font-weight: 600;
    }
    
    /* Error message styling */
    .version-error {
        background: linear-gradient(135deg, #FFD2D2 0%, #FFCDD2 100%);
        color: #C62828;
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid #F44336;
        box-shadow: 0 4px 15px rgba(216, 0, 12, 0.2);
        font-weight: 600;
    }
    
    /* Material section styling */
    .material-section {
        background: rgba(255, 255, 255, 0.9);
        padding: 25px;
        border-radius: 15px;
        margin: 20px 0;
        border: 2px solid #81C784;
        box-shadow: 0 6px 20px rgba(129, 199, 132, 0.2);
        backdrop-filter: blur(5px);
    }
    
    /* Summary section styling */
    .summary-section {
        background: linear-gradient(135deg, #E1F5FE 0%, #F3E5F5 100%);
        padding: 30px;
        border-radius: 20px;
        margin: 30px 0;
        border: 3px solid #4CAF50;
        box-shadow: 0 10px 30px rgba(76, 175, 80, 0.25);
    }
    
    .summary-section h2 {
        color: #2E7D32 !important;
        text-align: center;
        margin-bottom: 25px !important;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
    }
    
    .summary-section h3 {
        color: #388E3C !important;
        margin-top: 25px !important;
        font-size: 1.8rem !important;
    }
    
    .summary-section p {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        margin: 15px 0 !important;
        color: #2E7D32 !important;
    }
    
    .summary-section ul {
        font-size: 1.1rem !important;
        color: #388E3C !important;
    }
    
    /* Info box styling */
    .info-box {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #2196F3;
        margin: 15px 0;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 12px;
        border: 2px solid #81C784;
        margin: 10px;
        text-align: center;
        box-shadow: 0 6px 18px rgba(129, 199, 132, 0.2);
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(129, 199, 132, 0.3);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4) !important;
    }
    
    /* Input field styling */
    .stNumberInput > div > div > input {
        border: 2px solid #81C784 !important;
        border-radius: 8px !important;
        padding: 10px !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    .stSelectbox > div > div > div {
        border: 2px solid #81C784 !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Chart container styling */
    .chart-container {
        background: rgba(255, 255, 255, 0.95);
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
        border: 2px solid #E0E0E0;
    }
    
    /* Hide Streamlit menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: #F1F8E9;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #2E7D32, #1B5E20);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<h1 class="primary-header">🌿 Easy LCA Indicator </h1>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# VERSION MANAGEMENT SIDEBAR
# ------------------------------------------------------------------
st.sidebar.markdown('<div class="version-section">', unsafe_allow_html=True)
st.sidebar.markdown("## 📁 Version Management")

# Version Management Actions
version_action = st.sidebar.selectbox(
    "Choose Action:",
    ["New Assessment", "Save Current", "Load Version", "Manage Versions"]
)

if version_action == "Save Current":
    st.sidebar.markdown("### Save Current Assessment")
    version_name = st.sidebar.text_input("Version Name:", key="save_version_name")
    version_description = st.sidebar.text_area("Description (optional):", key="save_version_desc")
    
    if st.sidebar.button("💾 Save Version"):
        if version_name and st.session_state.current_assessment_data:
            success, message = st.session_state.version_manager.save_version(
                version_name, st.session_state.current_assessment_data, version_description
            )
            if success:
                st.sidebar.markdown(f'<div class="version-success">{message}</div>', unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f'<div class="version-error">{message}</div>', unsafe_allow_html=True)
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
            version_info = versions[selected_version]
            st.sidebar.write(f"**Description:** {version_info.get('description', 'No description')}")
            st.sidebar.write(f"**Created:** {version_info.get('created_at', 'Unknown')}")
            st.sidebar.write(f"**Materials:** {version_info.get('materials_count', 0)}")
            st.sidebar.write(f"**Total CO₂:** {version_info.get('total_co2', 0):.2f} kg")
            
            if st.sidebar.button("📂 Load Version"):
                data, message = st.session_state.version_manager.load_version(selected_version)
                if data:
                    # Store loaded data in session state
                    st.session_state.loaded_version_data = data
                    st.sidebar.success(message)
                    st.sidebar.info("Data loaded! Refresh the page to apply the loaded configuration.")
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
            if success:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.error(message)
        
        st.sidebar.markdown("### Version List")
        for name, info in versions.items():
            st.sidebar.write(f"**{name}**")
            st.sidebar.write(f"  📅 {info.get('created_at', 'Unknown')[:10]}")
            st.sidebar.write(f"  📊 {info.get('materials_count', 0)} materials")
            st.sidebar.write("---")
    else:
        st.sidebar.info("No versions to manage")

st.sidebar.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# GLOBAL INPUT: LIFETIME OF THE FINAL PRODUCT (in weeks)
# ------------------------------------------------------------------
# Check if we have loaded version data
default_lifetime = 52
if hasattr(st.session_state, 'loaded_version_data') and 'lifetime_weeks' in st.session_state.loaded_version_data:
    default_lifetime = st.session_state.loaded_version_data['lifetime_weeks']

lifetime_weeks = st.number_input("Enter the lifetime of the final product (in weeks):",
                                 min_value=1, value=default_lifetime, key="lifetime_weeks")
lifetime_years = lifetime_weeks / 52

# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------
def extract_number(value):
    """Extracts a float from a string, handling commas and text units."""
    try:
        return float(value)
    except ValueError:
        s = str(value).replace(',', '.')
        match = re.search(r"[-+]?\d*\.?\d+", s)
        return float(match.group()) if match else 0.0

def extract_material_data(sheet_df):
    """Reads Materials sheet dynamically and returns a materials_dict."""
    sheet_df.columns = [str(c).strip() for c in sheet_df.columns]
    expected_columns = [
        "Material name", "CO2e (kg)", "Recycled Content", "EoL",
        "Lifetime", "Comment", "Circularity", "Alternative Material"
    ]
    for col in expected_columns:
        if col not in sheet_df.columns:
            st.error(f"Error: '{col}' column is missing in Materials sheet.")
            return {}
    materials_dict = {}
    for _, row in sheet_df.iterrows():
        material_name = str(row["Material name"]).strip() if pd.notna(row["Material name"]) else ""
        if not material_name:
            continue
        materials_dict[material_name] = {
            "CO₂e (kg)": extract_number(row["CO2e (kg)"]),
            "Recycled Content": extract_number(row["Recycled Content"]),
            "EoL": str(row["EoL"]).strip() if pd.notna(row["EoL"]) else "Unknown",
            "Lifetime": str(row["Lifetime"]).strip() if pd.notna(row["Lifetime"]) else "Unknown",
            "Comment": str(row["Comment"]).strip() if pd.notna(row["Comment"]) and row["Comment"].strip() else "No comment",
            "Circularity": str(row["Circularity"]).strip() if pd.notna(row["Circularity"]) else "Unknown",
            "Alternative Material": str(row["Alternative Material"]).strip() if pd.notna(row["Alternative Material"]) else "None"
        }
    return materials_dict

def extract_processes_data(sheet_df):
    """Reads Processes sheet dynamically and returns a processes_dict."""
    sheet_df.columns = [str(c).strip().replace("₂", "2").replace("CO₂", "CO2")
                         for c in sheet_df.columns]
    proc_col = next((c for c in sheet_df.columns if 'process' in c.lower()), None)
    co2_col = next((c for c in sheet_df.columns if 'co2' in c.lower()), None)
    unit_col = next((c for c in sheet_df.columns if 'unit' in c.lower()), None)
    if not proc_col or not co2_col or not unit_col:
        st.error("Error: Could not detect correct column names in 'Processes' sheet. Please check Excel formatting.")
        return {}
    processes_dict = {}
    for _, row in sheet_df.iterrows():
        proc_name = str(row[proc_col]).strip() if pd.notna(row[proc_col]) else ""
        if not proc_name:
            continue
        processes_dict[proc_name] = {
            "CO₂e": extract_number(row[co2_col]),
            "Unit": str(row[unit_col]).strip() if pd.notna(row[unit_col]) else "Unknown"
        }
    return processes_dict

def lifetime_category(lifetime_value):
    """Converts a numeric lifetime value into a category: Short, Medium, or Long."""
    if lifetime_value < 5:
        return "Short"
    elif lifetime_value <= 15:
        return "Medium"
    else:
        return "Long"

# ------------------------------------------------------------------
# LOAD EXCEL FILE & DATA EXTRACTION
# ------------------------------------------------------------------
st.markdown("""
<div class="info-box">
    <h3 style="margin-top: 0; color: #1976D2;">📂 Upload Your Excel Database</h3>
    <p style="margin-bottom: 0;">Upload your Excel file containing Materials and Processes sheets to begin the LCA assessment.</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Excel Database", type=["xlsx"])
if not uploaded_file:
    st.info("👆 Please upload your Excel database file to continue with the assessment.")
    st.stop()

xls = pd.ExcelFile(uploaded_file)
df_materials = pd.read_excel(xls, sheet_name="Materials")
materials_dict = extract_material_data(df_materials)
df_processes = pd.read_excel(xls, sheet_name="Processes")
processes_dict = extract_processes_data(df_processes)

# ------------------------------------------------------------------
# MATERIAL SELECTION & PROCESSING
# ------------------------------------------------------------------
# Check if we have loaded version data for material selection
default_materials = []
if hasattr(st.session_state, 'loaded_version_data') and 'selected_materials' in st.session_state.loaded_version_data:
    default_materials = st.session_state.loaded_version_data['selected_materials']

selected_materials = st.multiselect("Select Materials", 
                                   options=list(materials_dict.keys()),
                                   default=default_materials)
if not selected_materials:
    st.info("Please select at least one material.")
    st.stop()

# Initialize accumulators and containers.
total_material_co2 = 0.0
total_process_co2 = 0.0
total_mass = 0.0
total_weighted_recycled = 0.0
eol_summary = {}
comparison_data = []
material_masses = {}
processing_data = {}

# Mapping for Circularity to numeric values.
circularity_mapping = {"High": 3, "Medium": 2, "Low": 1, "Not Circular": 0}

for material_name in selected_materials:
    st.markdown(f'<div class="material-section">', unsafe_allow_html=True)
    st.header(f"🔧 Material: {material_name}")
    mat_props = materials_dict[material_name]
    
    # Input mass - check for loaded data
    default_mass = 1.0
    if (hasattr(st.session_state, 'loaded_version_data') and 
        'material_masses' in st.session_state.loaded_version_data and
        material_name in st.session_state.loaded_version_data['material_masses']):
        default_mass = st.session_state.loaded_version_data['material_masses'][material_name]
    
    mass = st.number_input(f"Enter mass of {material_name} (kg)", 
                          min_value=0.0, value=default_mass, key=f"mass_{material_name}")
    material_masses[material_name] = mass
    
    total_mass += mass
    material_co2 = mass * mat_props["CO₂e (kg)"]
    total_material_co2 += material_co2
    total_weighted_recycled += mass * mat_props["Recycled Content"]
    
    st.write(f"**CO₂e per kg:** {mat_props['CO₂e (kg)']} kg")
    st.write(f"**Recycled Content:** {mat_props['Recycled Content']}%")
    st.write(f"**Lifetime:** {mat_props['Lifetime']}")
    st.write(f"**Circularity:** {mat_props['Circularity']}")
    st.write(f"**Comment:** {mat_props['Comment']}")
    st.write(f"**Alternative Material:** {mat_props['Alternative Material']}")
    
    # Save End-of-Life info.
    eol_summary[material_name] = mat_props["EoL"]
    
    # Processing steps - check for loaded data
    default_proc_steps = 0
    if (hasattr(st.session_state, 'loaded_version_data') and 
        'processing_data' in st.session_state.loaded_version_data and
        material_name in st.session_state.loaded_version_data['processing_data']):
        default_proc_steps = len(st.session_state.loaded_version_data['processing_data'][material_name])
    
    n_proc = int(st.number_input(f"How many processing steps for {material_name}?",
                                min_value=0, max_value=10, value=default_proc_steps, 
                                key=f"proc_steps_{material_name}"))
    
    proc_total = 0.0
    processing_data[material_name] = []
    
    for i in range(n_proc):
        # Check for loaded processing data
        default_process = ""
        default_amount = 1.0
        if (hasattr(st.session_state, 'loaded_version_data') and 
            'processing_data' in st.session_state.loaded_version_data and
            material_name in st.session_state.loaded_version_data['processing_data'] and
            i < len(st.session_state.loaded_version_data['processing_data'][material_name])):
            loaded_proc = st.session_state.loaded_version_data['processing_data'][material_name][i]
            default_process = loaded_proc.get('process', "")
            default_amount = loaded_proc.get('amount', 1.0)
        
        proc_selected = st.selectbox(f"Process #{i+1} for {material_name}",
                                   options=[""] + list(processes_dict.keys()),
                                   index=0 if default_process == "" else (list(processes_dict.keys()).index(default_process) + 1 if default_process in processes_dict else 0),
                                   key=f"process_{material_name}_{i}")
        
        if proc_selected:
            process_props = processes_dict.get(proc_selected, {})
            co2e_per_unit = process_props.get("CO₂e", 0)
            unit = process_props.get("Unit", "Unknown")
            amount_processed = st.number_input(f"Enter amount for '{proc_selected}' ({unit})",
                                             min_value=0.0, value=default_amount,
                                             key=f"amount_{material_name}_{i}")
            proc_total += amount_processed * co2e_per_unit
            
            # Store processing data
            processing_data[material_name].append({
                'process': proc_selected,
                'amount': amount_processed,
                'co2e_per_unit': co2e_per_unit,
                'unit': unit
            })
    
    total_process_co2 += proc_total
    
    # Prepare data for comparison charts.
    circ_value = circularity_mapping.get(mat_props["Circularity"].title(), 0)
    lifetime_numeric = extract_number(mat_props["Lifetime"])
    comparison_data.append({
        "Material": material_name,
        "CO2e per kg": mat_props["CO₂e (kg)"],
        "Recycled Content (%)": mat_props["Recycled Content"],
        "Circularity (mapped)": circ_value,
        "Circularity (text)": mat_props["Circularity"],
        "Lifetime (years)": lifetime_numeric,
        "Lifetime (text)": mat_props["Lifetime"]
    })
    
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# FINAL SUMMARY 
# ------------------------------------------------------------------
overall_co2 = total_material_co2 + total_process_co2
total_trees_equiv = overall_co2 / 22 
trees_equiv = overall_co2 / (22 * lifetime_years) 
weighted_recycled = (total_weighted_recycled / total_mass) if total_mass > 0 else 0

final_summary_html = f"""
<div class="summary-section">
<h2>🌍 Final Summary</h2>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0;">
    <div class="metric-card">
        <h3 style="color: #2E7D32; margin: 0;">♻️ Weighted Recycled Content  </h3>
        <p style="font-size: 0.75rem; margin: 10px 0; color: #4CAF50;">{weighted_recycled:.1f}%</p>
    </div>
    <div class="metric-card">
        <h3 style="color: #2E7D32; margin: 0;">🏭 Total CO₂ Impact (Materials) </h3>
        <p style="font-size: 0.75rem; margin: 10px 0; color: #4CAF50;">{total_material_co2:.1f} kg</p>
    </div>
    <div class="metric-card">
        <h3 style="color: #2E7D32; margin: 0;">🔧 Total CO₂ Impact (Processes) </h3>
        <p style="font-size: 0.75rem; margin: 10px 0; color: #4CAF50;">{total_process_co2:.1f} kg</p>
    </div>
    <div class="metric-card">
        <h3 style="color: #2E7D32; margin: 0;">🌍 Total Impact CO₂e per kg </h3>
        <p style="font-size: 0.75rem; margin: 10px 0; color: #D32F2F;">{overall_co2:.1f} kg</p>
    </div>
    <div class="metric-card">
        <h3 style="color: #2E7D32; margin: 0;">🌳 Tree Equivalent</h3>
        <p style="font-size: 0.75rem; margin: 10px 0; color: #2E7D32;">{trees_equiv:.1f} trees/year over {lifetime_years} years </p>
    </div>
    <div class="metric-card">
        <h3 style="color: #2E7D32; margin: 0;">Total Tree Equivalent 🌳</h3>
        <p style="font-size: 0.75rem; margin: 10px 0; color: #2E7D32;">{total_trees_equiv:.1f} trees </p>
    </div>
</div>
<h3 style="color: #388E3C; text-align: center; margin-top: 30px;">🔄 End-of-Life Summary</h3>
<div style="background: rgba(255,255,255,0.7); padding: 20px; border-radius: 10px; margin-top: 15px;">
<ul style="list-style-type: none; padding: 0;">
"""
for material, eol in eol_summary.items():
    final_summary_html += f'<li style="padding: 8px; margin: 5px 0; background: rgba(76,175,80,0.1); border-radius: 5px; border-left: 4px solid #4CAF50;"><strong>{material}</strong>: {eol}</li>'
final_summary_html += """
</ul>
</div>
</div>
"""

st.markdown(final_summary_html, unsafe_allow_html=True)

# Store assessment data for versioning
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

# Store final summary in session state for versioning.
st.session_state.final_summary_html = final_summary_html

# ------------------------------------------------------------------
# VISUALIZATION: SEPARATE BAR CHARTS FOR EACH ATTRIBUTE
# ------------------------------------------------------------------
st.markdown("## 📊 Comparison Visualizations")

df_compare = pd.DataFrame(comparison_data)
my_color_sequence = ['#2E7D32', '#388E3C', '#4CAF50', '#66BB6A', '#81C784']

# Create chart containers
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # CO₂e per kg Comparison Chart.
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
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Recycled Content (%) Comparison Chart.
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
    st.markdown('</div>', unsafe_allow_html=True)

col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Circularity Comparison Chart.
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
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    # Lifetime Comparison Chart.
    df_compare["Lifetime Category"] = df_compare["Lifetime (years)"].apply(lifetime_category)
    lifetime_cat_to_num = {"Short": 1, "Medium": 2, "Long": 3}
    df_compare["Lifetime"] = df_compare["Lifetime Category"].map(lifetime_cat_to_num)
    fig_lifetime = px.bar(
        df_compare,
        x="Material",
        y="Lifetime",
        color="Material",
        title="⏱️ Lifetime Comparison",
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
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------
# CLEAR LOADED DATA (to prevent interference with new assessments)
# ------------------------------------------------------------------
if hasattr(st.session_state, 'loaded_version_data'):
    del st.session_state.loaded_version_data
