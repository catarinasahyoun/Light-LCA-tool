# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, hashlib, secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

# =============================================================
# TCHAI — Easy LCA Indicator
# - Front page Sign-in (hard gate). No self-signup.
# - 3 pre-created accounts (can change password).
# - Avatar menu: account settings + sign out.
# - Sidebar: TCHAI logo only + nav.
# - Header: big TCHAI logo left, title center.
# - Navigation: Inputs alone; Workspace = Results/Comparison/Summary/Report/Versions.
# - Black & White UI, purple charts.
# - Report: HTML only (big logo, no duplicate title).
# - Database manager: preloaded, upload new, visible history, activate.
# =============================================================

st.set_page_config(
    page_title="TCHAI — Easy LCA Indicator",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Paths & constants
# -----------------------------
ASSETS = Path("assets"); ASSETS.mkdir(exist_ok=True)
USERS_FILE = ASSETS / "users.json"
DB_ROOT = ASSETS / "databases"; DB_ROOT.mkdir(exist_ok=True)
ACTIVE_DB_FILE = DB_ROOT / "active.json"
PURPLE = ['#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']

def _rerun():
    if hasattr(st, "rerun"): st.rerun()
    else:
        try: st.experimental_rerun()
        except Exception: pass

# -----------------------------
# Branding
# -----------------------------
LOGO_PATHS = [ASSETS / "tchai_logo.png", Path("tchai_logo.png")]
_logo_bytes = None
for p in LOGO_PATHS:
    if p.exists():
        _logo_bytes = p.read_bytes()
        break

def logo_tag(height=86):
    if not _logo_bytes:
        return "<span style='font-weight:900;font-size:28px'>TCHAI</span>"
    b64 = base64.b64encode(_logo_bytes).decode()
    return f"<img src='data:image/png;base64,{b64}' style='height:{height}px'/>"

st.markdown(
    """
    <style>
      .stApp { background:#fff; color:#000; }
      .metric { border:1px solid #111; border-radius:12px; padding:14px; text-align:center; }
      .brand-title { font-weight:900; font-size:26px; text-align:center; }
      .nav-note { color:#6b7280; font-size:12px; }
      .avatar { width:36px; height:36px; border-radius:9999px; background:#111; color:#fff;
                display:flex; align-items:center; justify-content:center; font-weight:800; }
      .stSelectbox div[data-baseweb="select"],
      .stNumberInput input,
      .stTextInput input,
      .stTextArea textarea { border:1px solid #111; }
    </style>
    """, unsafe_allow_html=True
)

# -----------------------------
# Auth
# -----------------------------
def _load_users(): 
    try: return json.loads(USERS_FILE.read_text())
    except: return {}
def _save_users(d:dict): USERS_FILE.write_text(json.dumps(d, indent=2))
def _hash(pw,salt): return hashlib.sha256((salt+pw).encode()).hexdigest()
def _initials(name): return (name[0] if name else "U").upper()

def _bootstrap_users():
    if USERS_FILE.exists():
        try: cur=json.loads(USERS_FILE.read_text())
        except: cur={}
    else: cur={}
    if cur: return
    defaults=["sustainability@tchai.nl","jillderegt@tchai.nl","veravanbeaumont@tchai.nl"]
    init={}
    for email in defaults:
        salt=secrets.token_hex(8)
        init[email]={"salt":salt,"hash":_hash("ChangeMe123!",salt),"created_at":datetime.now().isoformat()}
    _save_users(init)
_bootstrap_users()
if "auth_user" not in st.session_state: st.session_state.auth_user=None

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown(f"<div style='text-align:center'>{logo_tag(64)}</div>", unsafe_allow_html=True)
    if st.session_state.auth_user:
        page=st.radio("Navigate",["Inputs","Workspace","Settings"])
        st.markdown("<div class='nav-note'>Inputs are separate. Workspace has Results, Comparison, Summary, Report, Versions.</div>",unsafe_allow_html=True)
    else:
        page="Sign in"

# -----------------------------
# Header
# -----------------------------
cl,cm,cr=st.columns([0.18,0.64,0.18])
with cl: st.markdown(logo_tag(86),unsafe_allow_html=True)
with cm: st.markdown("<div class='brand-title'>Easy LCA Indicator</div>",unsafe_allow_html=True)
with cr:
    if st.session_state.auth_user:
        initials=_initials(st.session_state.auth_user)
        if hasattr(st,"popover"):
            with st.popover(f"👤 {initials}"):
                st.write(f"Signed in as **{st.session_state.auth_user}**")
                with st.form("pwchange",clear_on_submit=True):
                    cur=st.text_input("Current",type="password")
                    new=st.text_input("New",type="password")
                    conf=st.text_input("Confirm",type="password")
                    if st.form_submit_button("Change password"):
                        u=_load_users(); rec=u.get(st.session_state.auth_user)
                        if not rec or _hash(cur,rec["salt"])!=rec["hash"]: st.error("Wrong current password")
                        elif new!=conf: st.error("Mismatch")
                        else:
                            salt=secrets.token_hex(8); rec["salt"]=salt; rec["hash"]=_hash(new,salt)
                            u[st.session_state.auth_user]=rec; _save_users(u); st.success("Changed.")
                if st.button("Sign out"):
                    st.session_state.auth_user=None; _rerun()

# -----------------------------
# Sign in gate
# -----------------------------
if not st.session_state.auth_user:
    st.markdown("### Sign in to continue")
    u=st.text_input("Email"); p=st.text_input("Password",type="password")
    if st.button("Sign in"):
        users=_load_users(); rec=users.get(u)
        if not rec: st.error("Unknown user.")
        elif _hash(p,rec["salt"])!=rec["hash"]: st.error("Wrong password.")
        else: st.session_state.auth_user=u; _rerun()
    st.stop()

# -----------------------------
# Database management
# -----------------------------
def list_dbs(): return sorted(DB_ROOT.glob("*.xlsx"),key=lambda p:p.stat().st_mtime,reverse=True)
def set_active(p:Path): ACTIVE_DB_FILE.write_text(json.dumps({"path":str(p)})); _rerun()
def get_active()->Optional[Path]:
    if ACTIVE_DB_FILE.exists():
        try: p=Path(json.loads(ACTIVE_DB_FILE.read_text())["path"]); 
        except: p=None
        if p and p.exists(): return p
    for c in [ASSETS/"Refined database.xlsx",Path("Refined database.xlsx"),Path("database.xlsx")]:
        if c.exists(): return c
    return None
def load_active_excel():
    p=get_active()
    return pd.ExcelFile(str(p)) if p and p.exists() else None

# -----------------------------
# Data parsing
# -----------------------------
def extract_number(v):
    try: return float(v)
    except: 
        s=str(v).replace(',','.')
        m=re.search(r"[-+]?\d*\.?\d+",s)
        return float(m.group()) if m else 0.0
def parse_materials(df):
    df.columns=[str(c).strip() for c in df.columns]
    out={}
    for _,r in df.iterrows():
        n=str(r.get("Material name","")).strip()
        if not n: continue
        out[n]={"CO₂e (kg)":extract_number(r.get("CO2e (kg)",0)),
                "Recycled Content":extract_number(r.get("Recycled Content",0)),
                "EoL":str(r.get("EoL","")),
                "Lifetime":str(r.get("Lifetime","")),
                "Circularity":str(r.get("Circularity",""))}
    return out
def parse_processes(df):
    df.columns=[str(c).strip().replace("₂","2") for c in df.columns]
    out={}
    for _,r in df.iterrows():
        n=str(r.get("Process","")).strip()
        if not n: continue
        out[n]={"CO₂e":extract_number(r.get("CO2e",0)),"Unit":str(r.get("Unit",""))}
    return out

# -----------------------------
# Session state
# -----------------------------
if "materials" not in st.session_state: st.session_state.materials={}
if "processes" not in st.session_state: st.session_state.processes={}
if "assessment" not in st.session_state: st.session_state.assessment={"lifetime_weeks":52,"selected_materials":[],"material_masses":{},"processing_data":{}}

# -----------------------------
# Inputs
# -----------------------------
if page=="Inputs":
    xls=load_active_excel()
    if not xls: st.error("No database."); st.stop()
    st.session_state.materials=parse_materials(pd.read_excel(xls,"Materials"))
    st.session_state.processes=parse_processes(pd.read_excel(xls,"Processes"))
    st.session_state.assessment["lifetime_weeks"]=st.number_input("Lifetime weeks",1,9999,st.session_state.assessment["lifetime_weeks"])
    sel=st.multiselect("Materials",list(st.session_state.materials.keys()),st.session_state.assessment["selected_materials"])
    st.session_state.assessment["selected_materials"]=sel
    for m in sel:
        st.session_state.assessment["material_masses"][m]=st.number_input(f"Mass of {m}",0.0,9999.0,st.session_state.assessment["material_masses"].get(m,1.0))
        steps=st.session_state.assessment["processing_data"].setdefault(m,[])
        n=st.number_input(f"Steps for {m}",0,10,len(steps))
        if n<len(steps): steps[:]=steps[:n]
        else:
            for _ in range(n-len(steps)): steps.append({"process":"","amount":1.0,"co2e_per_unit":0.0,"unit":""})
        for i in range(n):
            proc=st.selectbox(f"Step {i+1}",[""]+list(st.session_state.processes.keys()),index=0,key=f"{m}_{i}_proc")
            if proc:
                pr=st.session_state.processes[proc]
                amt=st.number_input(f"Amount {proc}",0.0,9999.0,steps[i].get("amount",1.0),key=f"{m}_{i}_amt")
                steps[i]={"process":proc,"amount":amt,"co2e_per_unit":pr["CO₂e"],"unit":pr["Unit"]}

# -----------------------------
# Compute results
# -----------------------------
def compute():
    d=st.session_state.assessment; mats=st.session_state.materials
    totM=totP=totMass=weighted=0; eol={}; rows=[]
    for m in d["selected_materials"]:
        mass=d["material_masses"].get(m,0); prop=mats[m]; totMass+=mass
        totM+=mass*prop["CO₂e (kg)"]; weighted+=mass*prop["Recycled Content"]; eol[m]=prop["EoL"]
        for s in d["processing_data"].get(m,[]): totP+=s["amount"]*s["co2e_per_unit"]
        rows.append({"Material":m,"CO2e per kg":prop["CO₂e (kg)"],"Recycled Content":prop["Recycled Content"]})
    overall=totM+totP; years=d["lifetime_weeks"]/52
    return {"mat":totM,"proc":totP,"overall":overall,"recycled":(weighted/totMass if totMass else 0),"eol":eol,"comp":rows}

# -----------------------------
# Workspace
# -----------------------------
if page=="Workspace":
    if not st.session_state.assessment["selected_materials"]: st.info("Add materials first."); st.stop()
    R=compute(); tabs=st.tabs(["Results","Comparison","Summary","Report","Versions"])
    with tabs[0]:
        st.metric("Total CO₂ materials",f"{R['mat']:.1f}"); st.metric("Total CO₂ processes",f"{R['proc']:.1f}")
    with tabs[1]:
        df=pd.DataFrame(R["comp"]); fig=px.bar(df,x="Material",y="CO2e per kg",color="Material",color_discrete_sequence=PURPLE)
        st.plotly_chart(fig,use_container_width=True)
    with tabs[2]:
        st.metric("Overall CO₂",f"{R['overall']:.1f}"); st.json(R["eol"])
    with tabs[3]:
        html=f"<html><body>{logo_tag(120)}<h2>Report</h2><p>Total CO₂: {R['overall']:.1f} kg</p></body></html>"
        st.download_button("⬇️ Download HTML",html,"report.html","text/html")
    with tabs[4]:
        class VM:
            def __init__(s): s.dir=Path("lca_versions"); s.dir.mkdir(exist_ok=True); s.meta=s.dir/"meta.json"
            def _load(s): return json.loads(s.meta.read_text()) if s.meta.exists() else {}
            def _save(s,m): s.meta.write_text(json.dumps(m,indent=2))
            def save(s,name,data): m=s._load(); fp=s.dir/f"{name}.json"; fp.write_text(json.dumps(data)); m[name]={"file":fp.name}; s._save(m); return True,"Saved"
            def list(s): return s._load()
            def delete(s,name): m=s._load(); fp=s.dir/m[name]["file"]; 
            def delete(s,name): m=s._load(); fp=s.dir/m[name]["file"]; 
                if fp.exists(): fp.unlink(); del m[name]; s._save(m); return True,"Deleted"
        if "vm" not in st.session_state: st.session_state.vm=VM()
        vm=st.session_state.vm
        name=st.text_input("Save as"); 
        if st.button("Save"): st.success(vm.save(name,st.session_state.assessment)[1])
        meta=vm.list(); 
        if meta:
            sel=st.selectbox("Delete",list(meta.keys()))
            if st.button("🗑️ Delete"): st.success(vm.delete(sel)[1]); _rerun()

# -----------------------------
# Settings
# -----------------------------
if page=="Settings":
    st.subheader("Database Manager")
    file=st.file_uploader("Upload new DB",type="xlsx")
    if file: 
        p=DB_ROOT/f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.name}"
        with open(p,"wb") as f: f.write(file.getbuffer())
        set_active(p)
    st.write("Existing DBs:"); [st.write(f.name) for f in list_dbs()]
