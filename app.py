# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
from datetime import datetime
import os

# =========================
# Version Manager
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
            with open(self.metadata_file, "r") as f:
                return json.load(f)
        return {}

    def _save_metadata(self, metadata):
        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def save_version(self, version_name, assessment_data, description=""):
        meta = self._load_metadata()
        if version_name in meta:
            return False, f"Version '{version_name}' already exists!"

        payload = {
            "assessment_data": assessment_data,
            "timestamp": datetime.now().isoformat(),
            "description": description,
        }
        filename = f"{version_name}.json"
        filepath = os.path.join(self.storage_dir, filename)
        with open(filepath, "w") as f:
            json.dump(payload, f)

        meta[version_name] = {
            "filename": filename,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "materials_count": len(assessment_data.get("selected_materials", [])),
            "total_co2": assessment_data.get("overall_co2", 0),
            "lifetime_weeks": assessment_data.get("lifetime_weeks", 52),
        }
        self._save_metadata(meta)
        return True, f"Version '{version_name}' saved successfully!"

    def load_version(self, version_name):
        meta = self._load_metadata()
        if version_name not in meta:
            return None, f"Version '{version_name}' not found!"
        filepath = os.path.join(self.storage_dir, meta[version_name]["filename"])
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return data.get("assessment_data", {}), f"Version '{version_name}' loaded successfully!"
        except FileNotFoundError:
            return None, f"File for version '{version_name}' not found!"

    def list_versions(self):
        return self._load_metadata()

    def delete_version(self, version_name):
        meta = self._load_metadata()
        if version_name not in meta:
            return False, f"Version '{version_name}' not found!"
        filepath = os.path.join(self.storage_dir, meta[version_name]["filename"])
        try:
            os.remove(filepath)
        except FileNotFoundError:
            pass
        del meta[version_name]
        self._save_metadata(meta)
        return True, f"Version '{version_name}' deleted successfully!"

# =========================
# App Config & Minimal Style
# =========================
st.set_page_config(page_title="Easy LCA Indicator", page_icon="🌿", layout="wide")
st.markdown("<h1 style='text-align:center;margin-top:0'>🌿 Easy LCA Indicator</h1>", unsafe_allow_html=True)

# Versioning state
if "version_manager" not in st.session_state:
    st.session_state.version_manager = LCAVersionManager()
if "current_assessment_data" not in st.session_state:
    st.session_state.current_assessment_data = {}

# =========================
# Sidebar: Version Management
# =========================
st.sidebar.header("📁 Version Management")
action = st.sidebar.selectbox("Choose Action:", ["New Assessment", "Save Current", "Load Version", "Manage Versions"])

if action == "Save Current":
    st.sidebar.subheader("Save Current Assessment")
    v_name = st.sidebar.text_input("Version Name:")
    v_desc = st.sidebar.text_area("Description (optional):")
    if st.sidebar.button("💾 Save Version"):
        if not v_name:
            st.sidebar.error("Please enter a version name.")
        elif not st.session_state.current_assessment_data:
            st.sidebar.error("No assessment data to save yet.")
        else:
            ok, msg = st.session_state.version_manager.save_version(v_name, st.session_state.current_assessment_data, v_desc)
            st.sidebar.success(msg) if ok else st.sidebar.error(msg)

elif action == "Load Version":
    st.sidebar.subheader("Load Saved Version")
    versions = st.session_state.version_manager.list_versions()
    if not versions:
        st.sidebar.info("No saved versions.")
    else:
        sel = st.sidebar.selectbox("Select Version:", list(versions.keys()))
        if sel:
            info = versions[sel]
            st.sidebar.write(f"**Created:** {info.get('created_at', '')[:19]}")
            st.sidebar.write(f"**Materials:** {info.get('materials_count', 0)}")
            st.sidebar.write(f"**Total CO₂:** {info.get('total_co2', 0):.2f} kg")
            if st.sidebar.button("📂 Load Version"):
                data, msg = st.session_state.version_manager.load_version(sel)
                if data is None:
                    st.sidebar.error(msg)
                else:
                    st.session_state.loaded_version_data = data
                    st.sidebar.success(msg)

elif action == "Manage Versions":
    st.sidebar.subheader("Manage Versions")
    versions = st.session_state.version_manager.list_versions()
    if not versions:
        st.sidebar.info("Nothing to manage yet.")
    else:
        del_sel = st.sidebar.selectbox("Select Version to Delete:", list(versions.keys()))
        if st.sidebar.button("🗑️ Delete Version"):
            ok, msg = st.session_state.version_manager.delete_version(del_sel)
            st.sidebar.success(msg) if ok else st.sidebar.error(msg)
            st.rerun()
        st.sidebar.markdown("---")
        for name, meta in versions.items():
            st.sidebar.write(f"**{name}** — {meta.get('created_at','')[:19]} • {meta.get('materials_count',0)} materials")

# =========================
# Global Input
# =========================
default_weeks = 52
if hasattr(st.session_state, "loaded_version_data"):
    default_weeks = int(st.session_state.loaded_version_data.get("lifetime_weeks", default_weeks))

lifetime_weeks = st.number_input("Enter the lifetime of the final product (in weeks):", min_value=1, value=default_weeks)
lifetime_years = lifetime_weeks / 52

# =========================
# Helpers
# =========================
def extract_number(value):
    try:
        return float(value)
    except Exception:
        s = str(value).replace(",", ".")
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def lifetime_category(v):
    v = float(v)
    if v < 5: return "Short"
    if v <= 15: return "Medium"
    return "Long"

def extract_materials(df: pd.DataFrame):
    cols = [str(c).strip() for c in df.columns]
    need = ["Material name","CO2e (kg)","Recycled Content","EoL","Lifetime","Comment","Circularity","Alternative Material"]
    for col in need:
        if col not in cols:
            st.error(f"Materials sheet is missing column: '{col}'")
            return {}
    out = {}
    for _, r in df.iterrows():
        name = str(r["Material name"]).strip() if pd.notna(r["Material name"]) else ""
        if not name: continue
        out[name] = {
            "CO₂e (kg)": extract_number(r["CO2e (kg)"]),
            "Recycled Content": extract_number(r["Recycled Content"]),
            "EoL": str(r["EoL"]).strip() if pd.notna(r["EoL"]) else "Unknown",
            "Lifetime": str(r["Lifetime"]).strip() if pd.notna(r["Lifetime"]) else "Unknown",
            "Comment": (str(r["Comment"]).strip() if pd.notna(r["Comment"]) and str(r["Comment"]).strip() else "No comment"),
            "Circularity": str(r["Circularity"]).strip() if pd.notna(r["Circularity"]) else "Unknown",
            "Alternative Material": str(r["Alternative Material"]).strip() if pd.notna(r["Alternative Material"]) else "None",
        }
    return out

def extract_processes(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip().replace("₂","2").replace("CO₂","CO2") for c in df.columns]
    proc_col = next((c for c in df.columns if "process" in c.lower()), None)
    co2_col  = next((c for c in df.columns if "co2" in c.lower()), None)
    unit_col = next((c for c in df.columns if "unit" in c.lower()), None)
    if not proc_col or not co2_col or not unit_col:
        st.error("Processes sheet must include columns for process, CO2 and unit.")
        return {}
    out = {}
    for _, r in df.iterrows():
        n = str(r[proc_col]).strip() if pd.notna(r[proc_col]) else ""
        if not n: continue
        out[n] = {
            "CO₂e": extract_number(r[co2_col]),
            "Unit": str(r[unit_col]).strip() if pd.notna(r[unit_col]) else "Unknown",
        }
    return out

# =========================
# Upload Excel
# =========================
st.markdown("### 📂 Upload Your Excel Database (needs 'Materials' and 'Processes' sheets)")
upl = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
if not upl:
    st.info("Upload an Excel file to continue.")
    st.stop()

xls = pd.ExcelFile(upl)
try:
    mats_df = pd.read_excel(xls, sheet_name="Materials")
    procs_df = pd.read_excel(xls, sheet_name="Processes")
except Exception as e:
    st.error(f"Could not open required sheets. {e}")
    st.stop()

materials = extract_materials(mats_df)
processes = extract_processes(procs_df)
if not materials:
    st.stop()

# =========================
# Material selection
# =========================
default_selected = []
default_masses = {}
default_proc_map = {}

if hasattr(st.session_state, "loaded_version_data"):
    ld = st.session_state.loaded_version_data
    default_selected = ld.get("selected_materials", [])
    default_masses = ld.get("material_masses", {})
    default_proc_map = ld.get("processing_data", {})

selected = st.multiselect("Select Materials", options=list(materials.keys()), default=[m for m in default_selected if m in materials])
if not selected:
    st.info("Please select at least one material.")
    st.stop()

total_material_co2 = 0.0
total_process_co2 = 0.0
total_mass = 0.0
total_weighted_recycled = 0.0
eol_summary = {}
comparison_rows = []
material_masses = {}
processing_data = {}

circ_map = {"High":3,"Medium":2,"Low":1,"Not Circular":0}

for mat in selected:
    st.markdown(f"#### 🔧 {mat}")
    props = materials[mat]

    mass_default = float(default_masses.get(mat, 1.0))
    mass = st.number_input(f"Mass of {mat} (kg)", min_value=0.0, value=mass_default, key=f"mass_{mat}")
    material_masses[mat] = mass

    total_mass += mass
    total_material_co2 += mass * props["CO₂e (kg)"]
    total_weighted_recycled += mass * props["Recycled Content"]
    eol_summary[mat] = props["EoL"]

    st.caption(f"CO₂e/kg: {props['CO₂e (kg)']} · Recycled %: {props['Recycled Content']} · EoL: {props['EoL']}")
    st.caption(f"Circularity: {props['Circularity']} · Lifetime: {props['Lifetime']} · Alt: {props['Alternative Material']}")

    # processing
    existing_steps = default_proc_map.get(mat, [])
    n_default = len(existing_steps)
    n_steps = int(st.number_input(f"Processing steps for {mat}", min_value=0, max_value=10, value=n_default, key=f"steps_{mat}"))
    processing_data[mat] = []

    for i in range(n_steps):
        default_proc = existing_steps[i]["process"] if i < n_default else ""
        default_amt  = float(existing_steps[i].get("amount", 1.0)) if i < n_default else 1.0
        proc_list = [""] + list(processes.keys())
        idx = proc_list.index(default_proc) if default_proc in proc_list else 0

        proc = st.selectbox(f"Process #{i+1} for {mat}", options=proc_list, index=idx, key=f"proc_{mat}_{i}")
        if proc:
            pr = processes.get(proc, {})
            unit = pr.get("Unit","")
            co2_per = float(pr.get("CO₂e", 0))
            amt = st.number_input(f"Amount for '{proc}' ({unit})", min_value=0.0, value=default_amt, key=f"amt_{mat}_{i}")
            total_process_co2 += amt * co2_per
            processing_data[mat].append({"process": proc, "amount": amt, "co2e_per_unit": co2_per, "unit": unit})

    # comparison rows
    life_years = extract_number(props["Lifetime"])
    comparison_rows.append({
        "Material": mat,
        "CO2e per kg": props["CO₂e (kg)"],
        "Recycled Content (%)": props["Recycled Content"],
        "Circularity (mapped)": circ_map.get(props["Circularity"].title() if props["Circularity"] else "Not Circular", 0),
        "Circularity (text)": props["Circularity"],
        "Lifetime (years)": life_years,
        "Lifetime (text)": props["Lifetime"],
    })

# =========================
# Results
# =========================
overall_co2 = total_material_co2 + total_process_co2
weighted_recycled = (total_weighted_recycled / total_mass) if total_mass > 0 else 0.0
trees_equiv_year = overall_co2 / (22 * (lifetime_years if lifetime_years > 0 else 1e-9))
total_trees_equiv = overall_co2 / 22

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total CO₂ (materials)", f"{total_material_co2:.1f} kg")
c2.metric("Total CO₂ (processes)", f"{total_process_co2:.1f} kg")
c3.metric("Weighted recycled", f"{weighted_recycled:.1f}%")
c4.metric("Total CO₂ (overall)", f"{overall_co2:.1f} kg")

st.markdown("### 🌍 Final Summary")
st.write(f"- **Tree equivalent / year**: {trees_equiv_year:.1f}")
st.write(f"- **Total tree equivalent**: {total_trees_equiv:.1f}")
st.write("#### End-of-Life Summary")
for k, v in eol_summary.items():
    st.write(f"• **{k}** — {v}")

# Save assessment snapshot for versioning
st.session_state.current_assessment_data = {
    "lifetime_weeks": lifetime_weeks,
    "selected_materials": selected,
    "material_masses": material_masses,
    "processing_data": processing_data,
    "total_material_co2": total_material_co2,
    "total_process_co2": total_process_co2,
    "overall_co2": overall_co2,
    "weighted_recycled": weighted_recycled,
    "trees_equiv": trees_equiv_year,
    "eol_summary": eol_summary,
    "comparison_data": comparison_rows,
}

# =========================
# Charts
# =========================
st.markdown("## 📊 Comparison Visualizations")
dfc = pd.DataFrame(comparison_rows)
if not dfc.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(dfc, x="Material", y="CO2e per kg", color="Material", title="CO₂e per kg")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.bar(dfc, x="Material", y="Recycled Content (%)", color="Material", title="Recycled Content (%)")
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig3 = px.bar(dfc, x="Material", y="Circularity (mapped)", color="Material", title="Circularity")
        fig3.update_yaxes(tickmode="array", tickvals=[0,1,2,3], ticktext=["Not Circular","Low","Medium","High"])
        st.plotly_chart(fig3, use_container_width=True)
    with col4:
        dfc2 = dfc.copy()
        dfc2["Lifetime Category"] = dfc2["Lifetime (years)"].apply(lifetime_category)
        map_cat = {"Short":1,"Medium":2,"Long":3}
        dfc2["Lifetime"] = dfc2["Lifetime Category"].map(map_cat)
        fig4 = px.bar(dfc2, x="Material", y="Lifetime", color="Material", title="Lifetime")
        fig4.update_yaxes(tickmode="array", tickvals=[1,2,3], ticktext=["Short","Medium","Long"])
        st.plotly_chart(fig4, use_container_width=True)

# Clear loaded snapshot so new runs start clean
if hasattr(st.session_state, "loaded_version_data"):
    del st.session_state.loaded_version_data
