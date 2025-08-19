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
# TCHAI — Easy LCA Indicator (Black & White UI, Purple Charts)
# - Uses uploaded/extracted TCHAI logo (assets/tchai_logo.png or via Settings upload)
# - Black & white overall theme to match the brief
# - All charts in purple (PDF-like)
# - Sidebar radio navigation: Inputs / Results / Summary / Visuals / Versions / Settings
# - Sidebar reopen fixed by restoring Streamlit header + expanded sidebar
# =============================================================

st.set_page_config(page_title="Easy LCA Indicator — TCHAI", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

# -----------------------------
# Simple local auth (optional, kept from previous version)
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
    import hashlib as _h
    return _h.sha256((salt + pw).encode("utf-8")).hexdigest()

if "user" not in st.session_state:
    st.session_state.user = None

# -----------------------------
# Version manager (unchanged)
# -----------------------------
class LCAVersionManager:
    def __init__(self, storage_dir: str = "lca_versions"):
        self.storage_dir = storage_dir
        self.metadata_file = os.path.join(storage_dir, "lca_versions_metadata.json")
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    def _load_metadata(self):
        if os.path.exists(self.metadata_file):
            return json.loads(Path(self.metadata_file).read_text())
        return {}
    def _save_metadata(self, m):
        Path(self.metadata_file).write_text(json.dumps(m, indent=2))
    def save_version(self, version_name, assessment_data, description=""):
        m = self._load_metadata()
        if version_name in m:
            return False, f"Version '{version_name}' already exists!"
        fname = f"{version_name}.json"
        Path(self.storage_dir, fname).write_text(json.dumps({
            'assessment_data': assessment_data,
            'timestamp': datetime.now().isoformat(),
            'description': description
        }))
        m[version_name] = {
            'filename': fname,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'materials_count': len(assessment_data.get('selected_materials', [])),
            'total_co2': assessment_data.get('overall_co2', 0),
            'lifetime_weeks': assessment_data.get('lifetime_weeks', 52)
        }
        self._save_metadata(m)
        return True, f"Version '{version_name}' saved successfully!"
    def load_version(self, version_name):
        m = self._load_metadata()
        if version_name not in m:
            return None, f"Version '{version_name}' not found!"
        fp = Path(self.storage_dir, m[version_name]['filename'])
        if not fp.exists():
            return None, f"File for version '{version_name}' not found!"
        data = json.loads(fp.read_text())
        return data['assessment_data'], f"Version '{version_name}' loaded successfully!"
    def list_versions(self):
        return self._load_metadata()
    def delete_version(self, version_name):
        m = self._load_metadata()
        if version_name not in m:
            return False, f"Version '{version_name}' not found!"
        fp = Path(self.storage_dir, m[version_name]['filename'])
        if fp.exists():
            fp.unlink()
        del m[version_name]
        self._save_metadata(m)
        return True, f"Version '{version_name}' deleted successfully!"

if "version_manager" not in st.session_state:
    st.session_state.version_manager = LCAVersionManager()
if "current_assessment_data" not in st.session_state:
    st.session_state.current_assessment_data = {}

# -----------------------------
# Branding & theme
# -----------------------------
ASSETS = Path("assets"); ASSETS.mkdir(exist_ok=True)
LOGO_PATHS = [ASSETS/"tchai_logo.png", Path("tchai_logo.png")]
logo_bytes = None
for p in LOGO_PATHS:
    if p.exists():
        logo_bytes = p.read_bytes(); break

def logo_img_tag(height=42):
    if not logo_bytes:
        return "<span style='font-weight:800;color:#000'>TCHAI</span>"
    b64 = base64.b64encode(logo_bytes).decode("utf-8")
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

PURPLES = ['#6C2BD9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']

st.markdown(
    f"""
    <style>
      /* Black & White base */
      .stApp {{ background:#fff; color:#000; }}
      #MainMenu {{ visibility: visible; }} /* keep header so sidebar toggle is accessible */
      header {{ visibility: visible; }}
      footer {{ visibility: hidden; }}
      .topbar {{ display:flex; align-items:center; gap:12px; justify-content:center; margin: 0 0 1rem 0; }}
      .brand-title {{ font-weight:800; font-size:1.6rem; letter-spacing:.2px; color:#000; }}
      .card {{ border:1px solid #e5e7eb; border-radius:12px; padding:16px; background:#fff; }}
      .bw-section {{ border:1px solid #e5e7eb; border-radius:12px; padding:18px; margin:10px 0; }}
      .metric {{ border:1px solid #111; border-radius:10px; padding:12px; text-align:center; }}
      /* floating menu button (visible when sidebar collapsed too) */
      .menu-fab {{ position:fixed; left:16px; bottom:16px; z-index:9999; }}
      .menu-fab button {{ border:1px solid #000 !important; background:#fff !important; color:#000 !important; }}
    </style>
    """,
    unsafe_allow_html=True
)

# Header
c1,c2,c3 = st.columns([0.15,0.7,0.15])
with c1: st.markdown(f"<div style='display:flex;justify-content:center'>{logo_img_tag(44)}</div>", unsafe_allow_html=True)
with c2: st.markdown("<div class='topbar'><div class='brand-title'>Easy LCA Indicator</div></div>", unsafe_allow_html=True)
with c3:
    if st.session_state.user:
        st.markdown(f"<div style='text-align:right'>👋 <b>{st.session_state.user['full_name']}</b></div>", unsafe_allow_html=True)

# Floating menu (just a reminder; Streamlit's own toggle is in the header)
st.sidebar.write("")
st.markdown("<div class='menu-fab'>"+st.button("☰ Menu", key="open_menu").__str__()+"</div>", unsafe_allow_html=True)

# -----------------------------
# Sidebar: Nav + Auth + Versions quick links
# -----------------------------
with st.sidebar:
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:6px'>{logo_img_tag(36)}</div>", unsafe_allow_html=True)
    page = st.radio("Navigate", ["Inputs","Results","Final Summary","Visuals","Version Management","Settings"], index=0)
    st.markdown("---")
    st.caption("Sign in (local demo)")
    u = st.text_input("Username", key="auth_user")
    p = st.text_input("Password", type="password", key="auth_pass")
    cc1,cc2 = st.columns(2)
    if cc1.button("Sign in", use_container_width=True):
        users = _load_users(); rec = users.get(u)
        if rec and _hash_pw(p, rec.get('salt','')) == rec.get('pw_hash'):
            st.session_state.user = {"username": u, "full_name": rec.get("full_name", u)}
            st.success(f"Welcome {st.session_state.user['full_name']}!")
        else:
            st.error("Invalid credentials.")
    if cc2.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.experimental_rerun()
    with st.expander("Create account"):
        nu = st.text_input("New username"); nn = st.text_input("Full name")
        npw = st.text_input("New password", type="password")
        if st.button("Create", use_container_width=True):
            if not nu or not npw:
                st.error("Enter username & password.")
            else:
                users = _load_users()
                if nu in users:
                    st.error("Username exists.")
                else:
                    salt = uuid.uuid4().hex
                    users[nu] = {"pw_hash": _hash_pw(npw, salt), "salt": salt, "full_name": nn or nu}
                    _save_users(users); st.success("Account created.")

# -----------------------------
# Helpers for data extraction
# -----------------------------

def extract_number(value):
    try: return float(value)
    except Exception:
        s = str(value).replace(',', '.')
        import re as _re
        m = _re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def lifetime_category(v):
    v = extract_number(v)
    return "Short" if v < 5 else ("Medium" if v <= 15 else "Long")

def extract_material_data(df: pd.DataFrame):
    df.columns = [str(c).strip() for c in df.columns]
    need = ["Material name","CO2e (kg)","Recycled Content","EoL","Lifetime","Comment","Circularity","Alternative Material"]
    for c in need:
        if c not in df.columns:
            st.error(f"Missing column in Materials: '{c}'"); return {}
    out = {}
    for _,r in df.iterrows():
        name = str(r["Material name"]).strip() if pd.notna(r["Material name"]) else ""
        if not name: continue
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

def extract_processes_data(df: pd.DataFrame):
    df.columns = [str(c).strip().replace("₂","2").replace("CO₂","CO2") for c in df.columns]
    proc_col = next((c for c in df.columns if 'process' in c.lower()), None)
    co2_col = next((c for c in df.columns if 'co2' in c.lower()), None)
    unit_col = next((c for c in df.columns if 'unit' in c.lower()), None)
    if not proc_col or not co2_col or not unit_col:
        st.error("Could not detect column names in 'Processes'."); return {}
    out = {}
    for _,r in df.iterrows():
        pname = str(r[proc_col]).strip() if pd.notna(r[proc_col]) else ""
        if not pname: continue
        out[pname] = {"CO₂e": extract_number(r[co2_col]), "Unit": str(r[unit_col]).strip() if pd.notna(r[unit_col]) else "Unknown"}
    return out

# -----------------------------
# Data store in session
# -----------------------------
if "materials_dict" not in st.session_state:
    st.session_state.materials_dict = {}
if "processes_dict" not in st.session_state:
    st.session_state.processes_dict = {}
if "comparison_data" not in st.session_state:
    st.session_state.comparison_data = []

# -----------------------------
# PAGE: Inputs
# -----------------------------
if page == "Inputs":
    st.markdown("### Upload Excel Database", help="Materials & Processes sheets required")
    up = st.file_uploader("Excel (.xlsx)", type=["xlsx"])
    if up is not None:
        xls = pd.ExcelFile(up)
        st.session_state.materials_dict = extract_material_data(pd.read_excel(xls, sheet_name="Materials"))
        st.session_state.processes_dict = extract_processes_data(pd.read_excel(xls, sheet_name="Processes"))
        st.success("Database loaded.")
    elif not st.session_state.materials_dict:
        st.info("Upload your refined database to start.")
        st.stop()

    default_lifetime = st.session_state.current_assessment_data.get('lifetime_weeks', 52)
    lifetime_weeks = st.number_input("Enter the lifetime of the final product (in weeks):", min_value=1, value=default_lifetime, key="lifetime_weeks")
    st.session_state.current_assessment_data['lifetime_weeks'] = lifetime_weeks

    mats = list(st.session_state.materials_dict.keys())
    default_selected = st.session_state.current_assessment_data.get('selected_materials', [])
    selected_materials = st.multiselect("Select Materials", options=mats, default=default_selected)
    st.session_state.current_assessment_data['selected_materials'] = selected_materials

    # Per-material inputs
    material_masses = st.session_state.current_assessment_data.get('material_masses', {})
    processing_data = st.session_state.current_assessment_data.get('processing_data', {})

    for m in selected_materials:
        with st.container():
            st.markdown(f"#### {m}")
            mass = st.number_input(f"Mass of {m} (kg)", min_value=0.0, value=float(material_masses.get(m,1.0)), key=f"mass_{m}")
            material_masses[m] = mass
            processing_data.setdefault(m, [])
            n = st.number_input(f"How many processing steps for {m}?", min_value=0, max_value=10, value=len(processing_data[m]), key=f"steps_{m}")
            # normalize list length
            if n < len(processing_data[m]):
                processing_data[m] = processing_data[m][:n]
            else:
                for _ in range(n - len(processing_data[m])):
                    processing_data[m].append({'process':'','amount':1.0,'co2e_per_unit':0.0,'unit':''})
            for i in range(n):
                proc = st.selectbox(f"Process #{i+1} for {m}", options=['']+list(st.session_state.processes_dict.keys()), index= (['']+list(st.session_state.processes_dict.keys())).index(processing_data[m][i]['process']) if processing_data[m][i]['process'] in st.session_state.processes_dict else 0, key=f"proc_{m}_{i}")
                if proc:
                    props = st.session_state.processes_dict.get(proc, {})
                    unit = props.get('Unit','')
                    amount = st.number_input(f"Amount for '{proc}' ({unit})", min_value=0.0, value=float(processing_data[m][i].get('amount',1.0)), key=f"amt_{m}_{i}")
                    processing_data[m][i] = {'process':proc,'amount':amount,'co2e_per_unit':props.get('CO₂e',0.0),'unit':unit}
    st.session_state.current_assessment_data['material_masses'] = material_masses
    st.session_state.current_assessment_data['processing_data'] = processing_data

# -----------------------------
# Compute results helper (used by Results/Summary/Visuals)
# -----------------------------

def compute_results():
    mats = st.session_state.materials_dict; procs = st.session_state.processes_dict
    data = st.session_state.current_assessment_data
    selected = data.get('selected_materials', [])
    total_material_co2=total_process_co2=total_mass=total_weighted_recycled=0.0
    eol_summary={}; comparison=[]
    circularity_map = {"High":3, "Medium":2, "Low":1, "Not Circular":0}
    for name in selected:
        m = mats.get(name, {})
        mass = float(data.get('material_masses', {}).get(name, 0.0))
        total_mass += mass
        total_material_co2 += mass * float(m.get("CO₂e (kg)",0))
        total_weighted_recycled += mass * float(m.get("Recycled Content",0))
        eol_summary[name] = m.get("EoL","Unknown")
        steps = data.get('processing_data', {}).get(name, [])
        for s in steps:
            total_process_co2 += float(s.get('amount',0))*float(s.get('co2e_per_unit',0))
        comparison.append({
            'Material': name,
            'CO2e per kg': float(m.get("CO₂e (kg)",0)),
            'Recycled Content (%)': float(m.get("Recycled Content",0)),
            'Circularity (mapped)': circularity_map.get(str(m.get("Circularity","")) .title(),0),
            'Circularity (text)': m.get("Circularity","Unknown"),
            'Lifetime (years)': extract_number(m.get("Lifetime",0)),
            'Lifetime (text)': m.get("Lifetime","Unknown")
        })
    overall = total_material_co2 + total_process_co2
    lifetime_weeks = float(st.session_state.current_assessment_data.get('lifetime_weeks',52))
    lifetime_years = max(lifetime_weeks/52, 1e-9)
    trees_equiv = overall/(22*lifetime_years)
    total_trees = overall/22
    weighted_rc = (total_weighted_recycled/total_mass) if total_mass>0 else 0.0
    return dict(
        total_material_co2=total_material_co2,
        total_process_co2=total_process_co2,
        overall_co2=overall,
        lifetime_years=lifetime_years,
        trees_equiv=trees_equiv,
        total_trees_equiv=total_trees,
        weighted_recycled=weighted_rc,
        eol_summary=eol_summary,
        comparison=comparison
    )

# -----------------------------
# PAGE: Results
# -----------------------------
if page == "Results":
    if not st.session_state.current_assessment_data.get('selected_materials'):
        st.info("Go to Inputs page to choose materials."); st.stop()
    R = compute_results()
    cols = st.columns(3)
    cols[0].metric("Total CO₂ (materials)", f"{R['total_material_co2']:.1f} kg")
    cols[1].metric("Total CO₂ (processes)", f"{R['total_process_co2']:.1f} kg")
    cols[2].metric("Weighted recycled", f"{R['weighted_recycled']:.1f}%")

# -----------------------------
# PAGE: Final Summary
# -----------------------------
if page == "Final Summary":
    if not st.session_state.current_assessment_data.get('selected_materials'):
        st.info("Go to Inputs page to choose materials."); st.stop()
    R = compute_results()
    st.markdown("#### Final Summary")
    mc1,mc2,mc3 = st.columns(3)
    mc1.markdown(f"<div class='metric'><div>Total Impact CO₂e</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
    mc2.markdown(f"<div class='metric'><div>Tree Equivalent / year</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
    mc3.markdown(f"<div class='metric'><div>Total Trees</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
    st.markdown("##### End‑of‑Life Summary")
    for mat,eol in R['eol_summary'].items():
        st.write(f"• **{mat}** — {eol}")

# -----------------------------
# PAGE: Visuals (purple charts)
# -----------------------------
if page == "Visuals":
    if not st.session_state.current_assessment_data.get('selected_materials'):
        st.info("Go to Inputs page to choose materials."); st.stop()
    R = compute_results()
    df = pd.DataFrame(R['comparison'])
    if df.empty:
        st.info("No data yet."); st.stop()
    def style(fig):
        fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="#fff", font=dict(color="#000"), title_x=0.5)
        return fig
    c1,c2 = st.columns(2)
    with c1:
        fig = px.bar(df, x="Material", y="CO2e per kg", color="Material", title="CO₂e per kg", color_discrete_sequence=PURPLES)
        st.plotly_chart(style(fig), use_container_width=True)
    with c2:
        fig = px.bar(df, x="Material", y="Recycled Content (%)", color="Material", title="Recycled Content (%)", color_discrete_sequence=PURPLES)
        st.plotly_chart(style(fig), use_container_width=True)
    c3,c4 = st.columns(2)
    with c3:
        fig = px.bar(df, x="Material", y="Circularity (mapped)", color="Material", title="Circularity", color_discrete_sequence=PURPLES)
        fig.update_yaxes(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High'])
        st.plotly_chart(style(fig), use_container_width=True)
    with c4:
        df2 = df.copy(); df2["Lifetime Category"] = df2["Lifetime (years)"].apply(lifetime_category)
        MAP = {"Short":1,"Medium":2,"Long":3}; df2["Lifetime"] = df2["Lifetime Category"].map(MAP)
        fig = px.bar(df2, x="Material", y="Lifetime", color="Material", title="Lifetime", color_discrete_sequence=PURPLES)
        fig.update_yaxes(tickmode='array', tickvals=[1,2,3], ticktext=['Short','Medium','Long'])
        st.plotly_chart(style(fig), use_container_width=True)

# -----------------------------
# PAGE: Version Management
# -----------------------------
if page == "Version Management":
    st.subheader("Save / Load / Manage Versions")
    vm = st.session_state.version_manager
    tab1,tab2,tab3 = st.tabs(["Save","Load","Manage"])
    with tab1:
        name = st.text_input("Version name")
        desc = st.text_area("Description (optional)")
        if st.button("💾 Save Version"):
            data = st.session_state.current_assessment_data
            if not data:
                st.error("No assessment data to save.")
            else:
                ok,msg = vm.save_version(name, data, desc)
                st.success(msg) if ok else st.error(msg)
    with tab2:
        vers = vm.list_versions()
        if not vers: st.info("No versions saved yet.")
        else:
            choice = st.selectbox("Select version", list(vers.keys()))
            if st.button("📂 Load"):
                data,msg = vm.load_version(choice)
                if data:
                    st.session_state.current_assessment_data = data
                    st.success(msg)
                else:
                    st.error(msg)
    with tab3:
        vers = vm.list_versions()
        if not vers: st.info("Nothing to manage.")
        else:
            choice = st.selectbox("Delete version", list(vers.keys()))
            if st.button("🗑️ Delete", type="secondary"):
                ok,msg = vm.delete_version(choice)
                st.success(msg) if ok else st.error(msg)

# -----------------------------
# PAGE: Settings (logo upload, theme notes)
# -----------------------------
if page == "Settings":
    st.subheader("Branding")
    lg = st.file_uploader("Upload TCHAI logo (PNG)", type=["png"])
    if lg is not None:
        data = lg.read(); (ASSETS/"tchai_logo.png").write_bytes(data)
        st.success("Logo saved as assets/tchai_logo.png. Reload to apply.")
        st.image(data, caption="Preview", use_column_width=False)
    st.caption("Theme is black & white; charts are purple to match the PDF.")
