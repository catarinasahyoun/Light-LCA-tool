import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, os
from datetime import datetime
from pathlib import Path

# =============================================================
# TCHAI — Easy LCA Indicator (Revamped)
# Goals implemented from your review:
# - Black & White UI
# - All charts in purple (brand‑aligned)
# - Real TCHAI logo (from assets/tchai_logo.png or upload in Settings)
# - Ergonomic navigation via sidebar radio (pages)
# - Sidebar is visible by default, header/menu not hidden
# - Logical flow, robust validation, persistent session state
# - Report downloads (HTML + CSV)
# =============================================================

st.set_page_config(
    page_title="Easy LCA Indicator — TCHAI",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Branding (logo loader/uploader)
# -----------------------------
ASSETS = Path("assets"); ASSETS.mkdir(exist_ok=True)
LOGO_PATHS = [ASSETS/"tchai_logo.png", Path("tchai_logo.png")]
_logo_bytes = None
for p in LOGO_PATHS:
    if p.exists():
        _logo_bytes = p.read_bytes(); break

def logo_img_tag(height=42):
    if not _logo_bytes:
        return "<span style='font-weight:800;color:#000'>TCHAI</span>"
    b64 = base64.b64encode(_logo_bytes).decode("utf-8")
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

# -----------------------------
# Minimal local versioning (kept)
# -----------------------------
class LCAVersionManager:
    def __init__(self, storage_dir: str = "lca_versions"):
        self.dir = Path(storage_dir); self.dir.mkdir(exist_ok=True)
        self.meta = self.dir/"lca_versions_metadata.json"
    def _load_meta(self):
        return json.loads(self.meta.read_text()) if self.meta.exists() else {}
    def _save_meta(self, m):
        self.meta.write_text(json.dumps(m, indent=2))
    def save(self, name, data, desc=""):
        m = self._load_meta()
        if not name:
            return False, "Enter a version name."
        if name in m:
            return False, f"Version '{name}' already exists."
        fp = self.dir/f"{name}.json"
        fp.write_text(json.dumps({"assessment_data": data, "timestamp": datetime.now().isoformat(), "description": desc}))
        m[name] = {"filename": fp.name, "description": desc, "created_at": datetime.now().isoformat(),
                   "materials_count": len(data.get("selected_materials", [])),
                   "total_co2": data.get("overall_co2", 0),
                   "lifetime_weeks": data.get("lifetime_weeks", 52)}
        self._save_meta(m); return True, f"Saved '{name}'."
    def load(self, name):
        m = self._load_meta();
        if name not in m: return None, f"Version '{name}' not found."
        fp = self.dir/m[name]["filename"]
        if not fp.exists(): return None, "File missing for this version."
        return json.loads(fp.read_text())["assessment_data"], f"Loaded '{name}'."
    def list(self):
        return self._load_meta()
    def delete(self, name):
        m = self._load_meta();
        if name not in m: return False, f"Version '{name}' not found."
        fp = self.dir/m[name]["filename"]
        if fp.exists(): fp.unlink()
        del m[name]; self._save_meta(m); return True, f"Deleted '{name}'."

if "vm" not in st.session_state: st.session_state.vm = LCAVersionManager()

# -----------------------------
# Theme: B&W + purple charts (no hidden menu so sidebar toggle works)
# -----------------------------
PURPLE = ['#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']
st.markdown(
    """
    <style>
      .stApp{background:#fff;color:#000}
      .bw-card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:#fff}
      .metric{border:1px solid #111;border-radius:10px;padding:12px;text-align:center}
      .topbar{display:flex;align-items:center;gap:12px;justify-content:center;margin:0 0 1rem 0}
      .brand-title{font-weight:800;font-size:1.6rem;color:#000}
      /* controls */
      .stSelectbox div[data-baseweb="select"]{border:1px solid #111}
      .stNumberInput input{border:1px solid #111}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Session defaults
# -----------------------------
ss = st.session_state
for k,v in {
    "materials":{}, "processes":{}, "assessment":{
        "lifetime_weeks":52, "selected_materials":[],
        "material_masses":{}, "processing_data":{}
    }
}.items():
    if k not in ss: ss[k]=v

# -----------------------------
# Utilities
# -----------------------------

def extract_number(v):
    try: return float(v)
    except Exception:
        s=str(v).replace(',','.')
        m=re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def parse_materials(df: pd.DataFrame):
    cols = ["Material name","CO2e (kg)","Recycled Content","EoL","Lifetime","Comment","Circularity","Alternative Material"]
    df.columns = [str(c).strip() for c in df.columns]
    for c in cols:
        if c not in df.columns:
            st.error(f"Missing column in Materials: '{c}'"); return {}
    out={}
    for _,r in df.iterrows():
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

def parse_processes(df: pd.DataFrame):
    df.columns=[str(c).strip().replace('₂','2').replace('CO₂','CO2') for c in df.columns]
    pcol=next((c for c in df.columns if 'process' in c.lower()), None)
    ccol=next((c for c in df.columns if 'co2' in c.lower()), None)
    ucol=next((c for c in df.columns if 'unit' in c.lower()), None)
    if not pcol or not ccol or not ucol:
        st.error("Could not detect column names in 'Processes'."); return {}
    out={}
    for _,r in df.iterrows():
        name=str(r[pcol]).strip() if pd.notna(r[pcol]) else ""
        if not name: continue
        out[name]={"CO₂e": extract_number(r[ccol]), "Unit": str(r[ucol]).strip() if pd.notna(r[ucol]) else "Unknown"}
    return out

# -----------------------------
# Header (logo centered)
# -----------------------------
L,R = st.columns([0.2,0.8])
with L: st.markdown(f"<div style='display:flex;justify-content:center'>{logo_img_tag(48)}</div>", unsafe_allow_html=True)
with R: st.markdown("<div class='topbar'><div class='brand-title'>Easy LCA Indicator</div></div>", unsafe_allow_html=True)

# -----------------------------
# Sidebar Navigation
# -----------------------------
with st.sidebar:
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:8px'>{logo_img_tag(36)}</div>", unsafe_allow_html=True)
    page = st.radio("Navigate", ["Inputs","Results","Final Summary","Visuals","Version Management","Report","Settings"], index=0)
    st.caption("Tip: use the top‑left ▷ to toggle this sidebar.")

# -----------------------------
# Page: Inputs
# -----------------------------
if page == "Inputs":
    st.subheader("1) Upload Excel database")
    up = st.file_uploader("Excel (.xlsx) with 'Materials' and 'Processes' sheets", type=["xlsx"])
    if up is not None:
        xls = pd.ExcelFile(up)
        ss.materials = parse_materials(pd.read_excel(xls, sheet_name="Materials"))
        ss.processes = parse_processes(pd.read_excel(xls, sheet_name="Processes"))
        st.success("Database loaded.")
    elif not ss.materials:
        # fallback to local bundled files if present
        for candidate in [Path("Refined database.xlsx"), Path("database.xlsx")]:
            if candidate.exists():
                xls = pd.ExcelFile(candidate)
                ss.materials = parse_materials(pd.read_excel(xls, sheet_name="Materials"))
                ss.processes = parse_processes(pd.read_excel(xls, sheet_name="Processes"))
                st.info(f"Using bundled: {candidate.name}")
                break
        if not ss.materials:
            st.stop()

    st.subheader("2) Lifetime (weeks)")
    ss.assessment["lifetime_weeks"] = st.number_input("Enter the lifetime of the final product (in weeks)", min_value=1, value=int(ss.assessment.get("lifetime_weeks",52)))

    st.subheader("3) Materials & processes")
    mats = list(ss.materials.keys())
    ss.assessment["selected_materials"] = st.multiselect("Select materials", options=mats, default=ss.assessment.get("selected_materials", []))
    if not ss.assessment["selected_materials"]:
        st.info("Select at least one material."); st.stop()

    # Per‑material inputs
    for m in ss.assessment["selected_materials"]:
        st.markdown(f"### {m}")
        masses = ss.assessment.setdefault("material_masses", {})
        procs_data = ss.assessment.setdefault("processing_data", {})
        mass_default = float(masses.get(m, 1.0))
        masses[m] = st.number_input(f"Mass of {m} (kg)", min_value=0.0, value=mass_default, key=f"mass_{m}")
        st.caption(f"CO₂e/kg: {ss.materials[m]['CO₂e (kg)']} · Recycled %: {ss.materials[m]['Recycled Content']} · EoL: {ss.materials[m]['EoL']}")
        # steps
        steps = procs_data.setdefault(m, [])
        n = st.number_input(f"How many processing steps for {m}?", min_value=0, max_value=10, value=len(steps), key=f"steps_{m}")
        # resize list
        if n < len(steps): steps[:] = steps[:n]
        else:
            for _ in range(n-len(steps)): steps.append({"process":"","amount":1.0,"co2e_per_unit":0.0,"unit":""})
        for i in range(n):
            proc = st.selectbox(f"Process #{i+1}", options=['']+list(ss.processes.keys()), index=(['']+list(ss.processes.keys())).index(steps[i]['process']) if steps[i]['process'] in ss.processes else 0, key=f"proc_{m}_{i}")
            if proc:
                props = ss.processes.get(proc,{})
                unit = props.get('Unit','')
                amt = st.number_input(f"Amount for '{proc}' ({unit})", min_value=0.0, value=float(steps[i].get('amount',1.0)), key=f"amt_{m}_{i}")
                steps[i] = {"process":proc, "amount":amt, "co2e_per_unit":props.get('CO₂e',0.0), "unit":unit}

# -----------------------------
# Compute results (shared)
# -----------------------------

def compute_results():
    data = ss.assessment
    selected = data.get('selected_materials', [])
    mats = ss.materials; procs = ss.processes
    total_material=total_process=total_mass=weighted=0.0
    eol={}; cmp=[]
    circ_map={"High":3,"Medium":2,"Low":1,"Not Circular":0}
    for name in selected:
        m=mats.get(name,{}); mass=float(data.get('material_masses',{}).get(name,0))
        total_mass += mass
        total_material += mass*float(m.get('CO₂e (kg)',0))
        weighted += mass*float(m.get('Recycled Content',0))
        eol[name]=m.get('EoL','Unknown')
        for s in data.get('processing_data',{}).get(name,[]):
            total_process += float(s.get('amount',0))*float(s.get('co2e_per_unit',0))
        cmp.append({
            'Material':name,
            'CO2e per kg':float(m.get('CO₂e (kg)',0)),
            'Recycled Content (%)':float(m.get('Recycled Content',0)),
            'Circularity (mapped)':circ_map.get(str(m.get('Circularity','')).title(),0),
            'Circularity (text)':m.get('Circularity','Unknown'),
            'Lifetime (years)':extract_number(m.get('Lifetime',0)),
            'Lifetime (text)':m.get('Lifetime','Unknown')
        })
    overall=total_material+total_process
    years=max(data.get('lifetime_weeks',52)/52, 1e-9)
    return {
        'total_material_co2':total_material,
        'total_process_co2':total_process,
        'overall_co2':overall,
        'weighted_recycled': (weighted/total_mass if total_mass>0 else 0.0),
        'trees_equiv': overall/(22*years),
        'total_trees_equiv': overall/22,
        'lifetime_years': years,
        'eol_summary': eol,
        'comparison': cmp
    }

# -----------------------------
# Page: Results
# -----------------------------
if page == "Results":
    if not ss.assessment.get('selected_materials'): st.info("Choose materials on Inputs first."); st.stop()
    R = compute_results()
    c1,c2,c3 = st.columns(3)
    c1.metric("Total CO₂ (materials)", f"{R['total_material_co2']:.1f} kg")
    c2.metric("Total CO₂ (processes)", f"{R['total_process_co2']:.1f} kg")
    c3.metric("Weighted recycled", f"{R['weighted_recycled']:.1f}%")

# -----------------------------
# Page: Final Summary
# -----------------------------
if page == "Final Summary":
    if not ss.assessment.get('selected_materials'): st.info("Choose materials on Inputs first."); st.stop()
    R = compute_results()
    m1,m2,m3 = st.columns(3)
    m1.markdown(f"<div class='metric'><div>Total Impact CO₂e</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric'><div>Tree Equivalent / year</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric'><div>Total Trees</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
    st.markdown("#### End‑of‑Life Summary")
    for k,v in R['eol_summary'].items():
        st.write(f"• **{k}** — {v}")

# -----------------------------
# Page: Visuals (purple charts)
# -----------------------------
if page == "Visuals":
    if not ss.assessment.get('selected_materials'): st.info("Choose materials on Inputs first."); st.stop()
    R = compute_results(); df = pd.DataFrame(R['comparison'])
    if df.empty: st.info("No comparison data yet."); st.stop()
    def style(fig):
        fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="#fff", font=dict(color="#000"), title_x=0.5)
        return fig
    c1,c2 = st.columns(2)
    with c1:
        fig = px.bar(df, x="Material", y="CO2e per kg", color="Material", title="CO₂e per kg", color_discrete_sequence=PURPLE)
        st.plotly_chart(style(fig), use_container_width=True)
    with c2:
        fig = px.bar(df, x="Material", y="Recycled Content (%)", color="Material", title="Recycled Content (%)", color_discrete_sequence=PURPLE)
        st.plotly_chart(style(fig), use_container_width=True)
    c3,c4 = st.columns(2)
    with c3:
        fig = px.bar(df, x="Material", y="Circularity (mapped)", color="Material", title="Circularity", color_discrete_sequence=PURPLE)
        fig.update_yaxes(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High'])
        st.plotly_chart(style(fig), use_container_width=True)
    with c4:
        df2=df.copy();
        df2['Lifetime Category']=df2['Lifetime (years)'].apply(lambda x: 'Short' if extract_number(x)<5 else ('Medium' if extract_number(x)<=15 else 'Long'))
        MAP={"Short":1,"Medium":2,"Long":3}; df2['Lifetime']=df2['Lifetime Category'].map(MAP)
        fig = px.bar(df2, x="Material", y="Lifetime", color="Material", title="Lifetime", color_discrete_sequence=PURPLE)
        fig.update_yaxes(tickmode='array', tickvals=[1,2,3], ticktext=['Short','Medium','Long'])
        st.plotly_chart(style(fig), use_container_width=True)

# -----------------------------
# Page: Version Management
# -----------------------------
if page == "Version Management":
    vm = ss.vm
    t1,t2,t3 = st.tabs(["Save","Load","Manage"])
    with t1:
        name = st.text_input("Version name")
        desc = st.text_area("Description (optional)")
        if st.button("💾 Save Version"):
            data = {**ss.assessment}
            R = compute_results() if ss.assessment.get('selected_materials') else {}
            data.update(R)
            ok,msg = vm.save(name, data, desc)
            st.success(msg) if ok else st.error(msg)
    with t2:
        meta = vm.list()
        if not meta: st.info("No versions saved yet.")
        else:
            sel = st.selectbox("Select version", list(meta.keys()))
            if st.button("📂 Load"):
                data,msg = vm.load(sel)
                if data:
                    ss.assessment = data
                    st.success(msg)
                else:
                    st.error(msg)
    with t3:
        meta = vm.list()
        if not meta: st.info("Nothing to manage.")
        else:
            sel = st.selectbox("Delete version", list(meta.keys()))
            if st.button("🗑️ Delete", type="secondary"):
                ok,msg = vm.delete(sel); st.success(msg) if ok else st.error(msg)

# -----------------------------
# Page: Report (HTML + CSV)
# -----------------------------
if page == "Report":
    if not ss.assessment.get('selected_materials'): st.info("Choose materials on Inputs first."); st.stop()
    R = compute_results()
    project = st.text_input("Project name", value="Sample Project")
    notes = st.text_area("Executive notes (optional)")
    # HTML report
    logo = logo_img_tag(44)
    html = f"""
    <!doctype html><html><head><meta charset='utf-8'><title>LCA Report — {project}</title>
    <style>body{{font-family:Arial, sans-serif;margin:24px}} header{{display:flex;align-items:center;gap:12px;margin-bottom:8px}} .title{{font-weight:800;color:#000}} table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #e5e7eb;padding:6px 8px;text-align:left}}</style></head>
    <body><header>{logo}<div class='title'>TCHAI — Easy LCA Indicator</div></header>
    <div><b>Project:</b> {project}</div>
    <div style='margin:6px 0'><b>Total Emissions:</b> {R['overall_co2']:.2f} kg CO₂e</div>
    <h3>Summary</h3>
    <ul>
      <li>Weighted recycled: {R['weighted_recycled']:.1f}%</li>
      <li>Total CO₂ (materials): {R['total_material_co2']:.1f} kg</li>
      <li>Total CO₂ (processes): {R['total_process_co2']:.1f} kg</li>
      <li>Tree‑equivalent per year: {R['trees_equiv']:.1f}</li>
    </ul>
    <h3>End‑of‑Life</h3>
    <ul>{''.join([f"<li><b>{k}</b> — {v}</li>" for k,v in R['eol_summary'].items()])}</ul>
    <h3>Notes</h3><div>{notes or '—'}</div>
    </body></html>
    """
    st.download_button("⬇️ Download HTML report", data=html.encode("utf-8"), file_name=f"LCA_Report_{project.replace(' ','_')}.html", mime="text/html")
    # CSVs
    df = pd.DataFrame(R['comparison'])
    st.download_button("⬇️ Download CSV — Comparison", data=df.to_csv(index=False).encode('utf-8'), file_name=f"LCA_Comparison_{project.replace(' ','_')}.csv", mime="text/csv")
    summary = pd.DataFrame({
        'Metric':['Weighted Recycled %','Total CO2 (materials)','Total CO2 (processes)','Overall CO2','Trees/year','Total trees'],
        'Value':[R['weighted_recycled'],R['total_material_co2'],R['total_process_co2'],R['overall_co2'],R['trees_equiv'],R['total_trees_equiv']]
    })
    st.download_button("⬇️ Download CSV — Summary", data=summary.to_csv(index=False).encode('utf-8'), file_name=f"LCA_Summary_{project.replace(' ','_')}.csv", mime="text/csv")

# -----------------------------
# Page: Settings (logo upload)
# -----------------------------
if page == "Settings":
    st.subheader("Branding")
    lg = st.file_uploader("Upload TCHAI logo (PNG)", type=["png"])
    if lg is not None:
        data = lg.read(); (ASSETS/"tchai_logo.png").write_bytes(data)
        st.success("Logo saved to assets/tchai_logo.png. Reload to apply.")
        st.image(data, caption="Preview", use_column_width=False)
    st.caption("UI is black & white; charts are purple as requested.")
