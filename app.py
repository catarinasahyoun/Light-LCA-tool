import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, os, hashlib, secrets
from datetime import datetime
from pathlib import Path

# =============================================================
# TCHAI — Easy LCA Indicator (Auth + Header + Visuals centered)
# =============================================================
# Changes in this revision:
# 1) Added local Sign in / Create account (sidebar) with salted SHA256 hashes (users.json).
# 2) Top-left TCHAI logo, bigger; title centered. (Header visible — no hidden Streamlit header.)
# 3) Visuals page titles strongly centered; chart titles centered and bigger.
# 4) Preserves earlier B&W UI and purple charts.

st.set_page_config(page_title="Easy LCA Indicator — TCHAI", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

# ---------- Assets / Branding ----------
ASSETS = Path("assets"); ASSETS.mkdir(exist_ok=True)
LOGO_PATHS = [ASSETS/"tchai_logo.png", Path("tchai_logo.png")]
logo_bytes = None
for p in LOGO_PATHS:
    if p.exists(): logo_bytes = p.read_bytes(); break

def logo_tag(height=60):
    if not logo_bytes:
        return "<span style='font-weight:800'>TCHAI</span>"
    b64 = base64.b64encode(logo_bytes).decode()
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

# ---------- Simple Auth (local file) ----------
USERS_FILE = ASSETS/"users.json"
if not USERS_FILE.exists(): USERS_FILE.write_text(json.dumps({}))

def _load_users():
    try: return json.loads(USERS_FILE.read_text())
    except Exception: return {}

def _save_users(data): USERS_FILE.write_text(json.dumps(data, indent=2))

def _hash(pw, salt): return hashlib.sha256((salt+pw).encode()).hexdigest()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

with st.sidebar:
    st.markdown(f"<div style='display:flex;align-items:center;gap:10px'>{logo_tag(44)}<span style='font-weight:800;font-size:18px'>Easy LCA Indicator</span></div>", unsafe_allow_html=True)
    st.write("\n")
    st.subheader("Account")
    mode = st.radio("", ["Sign in","Create account"], horizontal=True)
    if mode == "Create account":
        new_user = st.text_input("Email / username", key="new_u")
        new_pw = st.text_input("Password", type="password", key="new_p")
        if st.button("Create account"):
            users = _load_users()
            if not new_user or not new_pw:
                st.error("Enter a username and password.")
            elif new_user in users:
                st.error("Account already exists.")
            else:
                salt = secrets.token_hex(8)
                users[new_user] = {"salt": salt, "hash": _hash(new_pw, salt), "created_at": datetime.now().isoformat()}
                _save_users(users)
                st.success("Account created. You can sign in now.")
    else:
        u = st.text_input("Email / username", key="login_u")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Sign in"):
            users = _load_users(); rec = users.get(u)
            if not rec: st.error("User not found.")
            elif _hash(p, rec["salt"]) != rec["hash"]: st.error("Wrong password.")
            else:
                st.session_state.auth_user = u
                st.success(f"Signed in as {u}")
    if st.session_state.auth_user:
        if st.button("Sign out"):
            st.session_state.auth_user = None

# Gate the app until signed in
if not st.session_state.auth_user:
    st.info("Please sign in (or create an account) in the sidebar to use the tool.")
    st.stop()

# ---------- Minimal B&W theme with purple charts ----------
PURPLE = ['#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']
st.markdown(
    """
    <style>
      .stApp{background:#fff;color:#000}
      .bw-card{border:1px solid #e5e7eb;border-radius:12px;padding:16px;background:#fff}
      .metric{border:1px solid #111;border-radius:10px;padding:12px;text-align:center}
      .chart-title{font-size:20px;font-weight:700;text-align:center;margin:6px 0 2px}
      .header-wrap{display:flex;align-items:center;gap:14px}
      .brand-title{font-weight:900;font-size:28px}
      /* inputs */
      .stSelectbox div[data-baseweb="select"], .stNumberInput input{border:1px solid #111}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header (logo bigger left, title centered) ----------
left, mid, right = st.columns([0.2,0.6,0.2])
with left:
    st.markdown(f"<div class='header-wrap'>{logo_tag(64)}</div>", unsafe_allow_html=True)
with mid:
    st.markdown("<div class='brand-title' style='text-align:center'>Easy LCA Indicator</div>", unsafe_allow_html=True)
with right:
    st.write("")

# ---------- Versioning helper ----------
class LCAVersionManager:
    def __init__(self, storage_dir: str = "lca_versions"):
        self.dir = Path(storage_dir); self.dir.mkdir(exist_ok=True)
        self.meta = self.dir/"lca_versions_metadata.json"
    def _load(self):
        return json.loads(self.meta.read_text()) if self.meta.exists() else {}
    def _save(self, m): self.meta.write_text(json.dumps(m, indent=2))
    def save(self, name, data, desc=""):
        m=self._load()
        if not name: return False, "Enter a version name."
        if name in m: return False, f"Version '{name}' exists."
        fp=self.dir/f"{name}.json"; fp.write_text(json.dumps({"assessment_data":data,"timestamp":datetime.now().isoformat(),"description":desc}))
        m[name]={"filename":fp.name,"description":desc,"created_at":datetime.now().isoformat(),"materials_count":len(data.get('selected_materials',[])),"total_co2":data.get('overall_co2',0),"lifetime_weeks":data.get('lifetime_weeks',52)}
        self._save(m); return True, f"Saved '{name}'."
    def list(self): return self._load()
    def load(self, name):
        m=self._load();
        if name not in m: return None, "Not found"
        fp=self.dir/m[name]["filename"]
        if not fp.exists(): return None, "File missing"
        return json.loads(fp.read_text())["assessment_data"], "Loaded"
    def delete(self, name):
        m=self._load();
        if name not in m: return False, "Not found"
        fp=self.dir/m[name]["filename"]
        if fp.exists(): fp.unlink()
        del m[name]; self._save(m); return True, "Deleted"

if "vm" not in st.session_state: st.session_state.vm = LCAVersionManager()

# ---------- Sidebar Nav ----------
with st.sidebar:
    page = st.radio("Navigate", ["Inputs","Results","Final Summary","Visuals","Version Management","Report","Settings"], index=0)

# ---------- Helpers ----------

def extract_number(v):
    try: return float(v)
    except Exception:
        s=str(v).replace(',', '.')
        m=re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def parse_materials(df):
    cols=["Material name","CO2e (kg)","Recycled Content","EoL","Lifetime","Comment","Circularity","Alternative Material"]
    df.columns=[str(c).strip() for c in df.columns]
    for c in cols:
        if c not in df.columns:
            st.error(f"Missing column: {c}"); return {}
    out={}
    for _,r in df.iterrows():
        n=str(r["Material name"]).strip() if pd.notna(r["Material name"]) else ""
        if not n: continue
        out[n]={
            "CO₂e (kg)": extract_number(r["CO2e (kg)"]),
            "Recycled Content": extract_number(r["Recycled Content"]),
            "EoL": str(r["EoL"]).strip() if pd.notna(r["EoL"]) else "Unknown",
            "Lifetime": str(r["Lifetime"]).strip() if pd.notna(r["Lifetime"]) else "Unknown",
            "Comment": str(r["Comment"]).strip() if (pd.notna(r["Comment"]) and str(r["Comment"]).strip()) else "No comment",
            "Circularity": str(r["Circularity"]).strip() if pd.notna(r["Circularity"]) else "Unknown",
            "Alternative Material": str(r["Alternative Material"]).strip() if pd.notna(r["Alternative Material"]) else "None",
        }
    return out

def parse_processes(df):
    df.columns=[str(c).strip().replace('₂','2').replace('CO₂','CO2') for c in df.columns]
    pcol=next((c for c in df.columns if 'process' in c.lower()), None)
    ccol=next((c for c in df.columns if 'co2' in c.lower()), None)
    ucol=next((c for c in df.columns if 'unit' in c.lower()), None)
    if not pcol or not ccol or not ucol:
        st.error("Could not detect columns in 'Processes'."); return {}
    out={}
    for _,r in df.iterrows():
        name=str(r[pcol]).strip() if pd.notna(r[pcol]) else ""
        if not name: continue
        out[name]={"CO₂e": extract_number(r[ccol]), "Unit": str(r[ucol]).strip() if pd.notna(r[ucol]) else "Unknown"}
    return out

# ---------- Pages ----------
if page=="Inputs":
    st.subheader("Upload Excel database")
    up = st.file_uploader("Excel (.xlsx) with 'Materials' and 'Processes' sheets", type=["xlsx"])
    if up is None:
        st.info("Upload the Excel to start.")
        st.stop()
    xls=pd.ExcelFile(up)
    st.session_state.materials=parse_materials(pd.read_excel(xls, sheet_name="Materials"))
    st.session_state.processes=parse_processes(pd.read_excel(xls, sheet_name="Processes"))
    st.success("Database loaded.")

    st.subheader("Lifetime (weeks)")
    st.session_state.lifetime_weeks = st.number_input("", min_value=1, value=int(st.session_state.get("lifetime_weeks",52)))

    st.subheader("Materials & processes")
    mats=list(st.session_state.materials.keys())
    sel = st.multiselect("Select materials", options=mats, default=st.session_state.get("selected_materials",[]))
    st.session_state.selected_materials = sel

    for m in sel:
        st.markdown(f"### {m}")
        mass = st.number_input(f"Mass of {m} (kg)", min_value=0.0, value=float(st.session_state.get('material_masses',{}).get(m,1.0)), key=f"mass_{m}")
        st.session_state.setdefault('material_masses',{})[m]=mass
        props = st.session_state.materials[m]
        st.caption(f"CO₂e/kg: {props['CO₂e (kg)']} · Recycled %: {props['Recycled Content']} · EoL: {props['EoL']}")
        steps_key = f"steps_{m}"
        n = st.number_input(f"How many processing steps for {m}?", min_value=0, max_value=10, value=len(st.session_state.setdefault('processing_data',{}).get(m,[])))
        steps = st.session_state.setdefault('processing_data',{}).setdefault(m, [])
        # resize
        if n < len(steps): steps[:] = steps[:int(n)]
        else:
            for _ in range(int(n)-len(steps)):
                steps.append({"process":"","amount":1.0,"co2e_per_unit":0.0,"unit":""})
        for i in range(int(n)):
            proc = st.selectbox(f"Process #{i+1}", options=['']+list(st.session_state.processes.keys()), index=(['']+list(st.session_state.processes.keys())).index(steps[i]['process']) if steps[i]['process'] in st.session_state.processes else 0, key=f"proc_{m}_{i}")
            if proc:
                pr = st.session_state.processes[proc]
                amt = st.number_input(f"Amount for '{proc}' ({pr.get('Unit','')})", min_value=0.0, value=float(steps[i].get('amount',1.0)), key=f"amt_{m}_{i}")
                steps[i] = {"process":proc, "amount":amt, "co2e_per_unit":pr.get('CO₂e',0.0), "unit":pr.get('Unit','')}

# shared computation

def compute_results():
    ss = st.session_state
    sel = ss.get('selected_materials', [])
    mats = ss.get('materials', {})
    procs = ss.get('processing_data', {})
    total_material=total_process=total_mass=weighted=0.0
    eol={}; cmp=[]
    circ_map={"High":3,"Medium":2,"Low":1,"Not Circular":0}
    for name in sel:
        m=mats.get(name,{}); mass=float(ss.get('material_masses',{}).get(name,0))
        total_mass += mass
        total_material += mass*float(m.get('CO₂e (kg)',0))
        weighted += mass*float(m.get('Recycled Content',0))
        eol[name]=m.get('EoL','Unknown')
        for s in procs.get(name,[]):
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
    overall = total_material+total_process
    years = max(ss.get('lifetime_weeks',52)/52, 1e-9)
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

if page=="Results":
    if not st.session_state.get('selected_materials'): st.info("Add inputs first."); st.stop()
    R=compute_results()
    c1,c2,c3 = st.columns(3)
    c1.metric("Total CO₂ (materials)", f"{R['total_material_co2']:.1f} kg")
    c2.metric("Total CO₂ (processes)", f"{R['total_process_co2']:.1f} kg")
    c3.metric("Weighted recycled", f"{R['weighted_recycled']:.1f}%")

if page=="Final Summary":
    if not st.session_state.get('selected_materials'): st.info("Add inputs first."); st.stop()
    R=compute_results()
    m1,m2,m3=st.columns(3)
    m1.markdown(f"<div class='metric'><div>Total Impact CO₂e</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric'><div>Tree Equivalent / year</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric'><div>Total Trees</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
    st.markdown("#### End‑of‑Life Summary")
    for k,v in R['eol_summary'].items(): st.write(f"• **{k}** — {v}")

if page=="Visuals":
    if not st.session_state.get('selected_materials'): st.info("Add inputs first."); st.stop()
    R=compute_results(); df=pd.DataFrame(R['comparison'])
    if df.empty: st.info("No data yet."); st.stop()
    st.markdown("<div class='chart-title'>Comparison Visualizations</div>", unsafe_allow_html=True)
    def style(fig):
        fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="#fff", font=dict(color="#000", size=14), title_x=0.5, title_font_size=20)
        return fig
    c1,c2=st.columns(2)
    with c1:
        fig=px.bar(df, x="Material", y="CO2e per kg", color="Material", title="CO₂e per kg", color_discrete_sequence=PURPLE)
        st.plotly_chart(style(fig), use_container_width=True)
    with c2:
        fig=px.bar(df, x="Material", y="Recycled Content (%)", color="Material", title="Recycled Content (%)", color_discrete_sequence=PURPLE)
        st.plotly_chart(style(fig), use_container_width=True)
    c3,c4=st.columns(2)
    with c3:
        fig=px.bar(df, x="Material", y="Circularity (mapped)", color="Material", title="Circularity", color_discrete_sequence=PURPLE)
        fig.update_yaxes(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High'])
        st.plotly_chart(style(fig), use_container_width=True)
    with c4:
        d=df.copy(); d['Lifetime Category']=d['Lifetime (years)'].apply(lambda x: 'Short' if extract_number(x)<5 else ('Medium' if extract_number(x)<=15 else 'Long'))
        MAP={"Short":1,"Medium":2,"Long":3}; d['Lifetime']=d['Lifetime Category'].map(MAP)
        fig=px.bar(d, x="Material", y="Lifetime", color="Material", title="Lifetime", color_discrete_sequence=PURPLE)
        fig.update_yaxes(tickmode='array', tickvals=[1,2,3], ticktext=['Short','Medium','Long'])
        st.plotly_chart(style(fig), use_container_width=True)

if page=="Version Management":
    vm=st.session_state.vm
    t1,t2,t3=st.tabs(["Save","Load","Manage"])
    with t1:
        name=st.text_input("Version name")
        desc=st.text_area("Description (optional)")
        if st.button("💾 Save Version"):
            data={**st.session_state}
            R=compute_results() if st.session_state.get('selected_materials') else {}
            payload={
                'lifetime_weeks': st.session_state.get('lifetime_weeks',52),
                'selected_materials': st.session_state.get('selected_materials',[]),
                'material_masses': st.session_state.get('material_masses',{}),
                'processing_data': st.session_state.get('processing_data',{}),
                **R
            }
            ok,msg=vm.save(name, payload, desc); st.success(msg) if ok else st.error(msg)
    with t2:
        meta=vm.list()
        if not meta: st.info("No versions yet.")
        else:
            sel=st.selectbox("Select version", list(meta.keys()))
            if st.button("📂 Load"):
                data,msg=vm.load(sel)
                if data:
                    st.session_state.lifetime_weeks = data.get('lifetime_weeks',52)
                    st.session_state.selected_materials = data.get('selected_materials',[])
                    st.session_state.material_masses = data.get('material_masses',{})
                    st.session_state.processing_data = data.get('processing_data',{})
                    st.success(msg)
                else: st.error(msg)
    with t3:
        meta=vm.list()
        if not meta: st.info("Nothing to manage.")
        else:
            sel=st.selectbox("Delete version", list(meta.keys()))
            if st.button("🗑️ Delete", type="secondary"):
                ok,msg=vm.delete(sel); st.success(msg) if ok else st.error(msg)

if page=="Report":
    if not st.session_state.get('selected_materials'): st.info("Add inputs first."); st.stop()
    R=compute_results()
    project=st.text_input("Project name", value="Sample Project")
    notes=st.text_area("Executive notes")
    html=f"""
    <!doctype html><html><head><meta charset='utf-8'><title>LCA Report — {project}</title>
    <style>body{{font-family:Arial,sans-serif;margin:24px}} header{{display:flex;align-items:center;gap:12px}} .title{{font-weight:800}} th,td{{border:1px solid #eee;padding:6px 8px}} table{{border-collapse:collapse}}</style></head>
    <body>
      <header>{logo_tag(44)}<div class='title'>TCHAI — Easy LCA Indicator</div></header>
      <h2 style='text-align:center'>Summary</h2>
      <ul>
        <li>Total CO₂e: {R['overall_co2']:.2f} kg</li>
        <li>Weighted recycled: {R['weighted_recycled']:.1f}%</li>
        <li>Materials: {R['total_material_co2']:.1f} kg · Processes: {R['total_process_co2']:.1f} kg</li>
        <li>Trees/year: {R['trees_equiv']:.1f} · Total trees: {R['total_trees_equiv']:.1f}</li>
      </ul>
      <h3>End‑of‑Life</h3>
      <ul>{''.join([f"<li><b>{k}</b> — {v}</li>" for k,v in R['eol_summary'].items()])}</ul>
      <h3>Notes</h3><div>{notes or '—'}</div>
    </body></html>
    """
    st.download_button("⬇️ Download HTML report", data=html.encode(), file_name=f"LCA_Report_{project.replace(' ','_')}.html", mime="text/html")

if page=="Settings":
    st.subheader("Branding")
    up = st.file_uploader("Upload TCHAI logo (PNG)", type=["png"])
    if up is not None:
        data = up.read(); (ASSETS/"tchai_logo.png").write_bytes(data); st.success("Logo saved. Reload to apply.")
        st.image(data, caption="Preview", width=220)
