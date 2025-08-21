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
# - 3 pre-created accounts (change password possible).
# - Sign in page gates everything.
# - Avatar menu: account settings + sign out.
# - Sidebar: TCHAI logo only.
# - Header: big TCHAI logo left, title center.
# - Inputs page separate, Workspace = Results/Comparison/Summary/Report/Versions.
# - Black & White UI, purple charts.
# - Report: HTML only (download).
# - Database manager: upload new DB, list, activate.
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

# -----------------------------
# Styling
# -----------------------------
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
        try: p=Path(json.loads(ACTIVE_DB_FILE.read_text())["path"])
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

# -----------------------------
# Session state
# -----------------------------
if "assessment" not in st.session_state: 
    st.session_state.assessment={"lifetime_weeks":52,"selected_materials":[],"material_masses":{},"processing_data":{}}

# -----------------------------
# Workspace
# -----------------------------
if page=="Workspace":
    if not st.session_state.assessment["selected_materials"]:
        st.info("Add materials first.")
        st.stop()
    R={"overall":42.0,"mat":20.0,"proc":22.0,"eol":{"Steel":"Recycle"},"comp":[{"Material":"Steel","CO2e per kg":2.0,"Recycled Content":50}]}
    tabs=st.tabs(["Results","Comparison","Summary","Report","Versions"])
    with tabs[0]:
        st.metric("Total CO₂ materials",f"{R['mat']:.1f}")
        st.metric("Total CO₂ processes",f"{R['proc']:.1f}")
    with tabs[1]:
        df=pd.DataFrame(R["comp"])
        fig=px.bar(df,x="Material",y="CO2e per kg",color="Material",color_discrete_sequence=PURPLE)
        st.plotly_chart(fig,use_container_width=True)
    with tabs[2]:
        st.metric("Overall CO₂",f"{R['overall']:.1f}")
        st.json(R["eol"])
    with tabs[3]:
        html=f"<html><body>{logo_tag(120)}<h2>Report</h2><p>Total CO₂: {R['overall']:.1f} kg</p></body></html>"
        st.download_button("⬇️ Download HTML",html,"report.html","text/html")
    with tabs[4]:
        class VM:
            def __init__(self):
                self.dir=Path("lca_versions"); self.dir.mkdir(exist_ok=True)
                self.meta=self.dir/"meta.json"
            def _load(self): return json.loads(self.meta.read_text()) if self.meta.exists() else {}
            def _save(self,m): self.meta.write_text(json.dumps(m,indent=2))
            def save(self,name,data):
                m=self._load(); fp=self.dir/f"{name}.json"; fp.write_text(json.dumps(data))
                m[name]={"file":fp.name}; self._save(m); return True,"Saved"
            def list(self): return self._load()
            def delete(self,name):
                m=self._load(); fp=self.dir/m[name]["file"]
                if fp.exists(): fp.unlink()
                del m[name]; self._save(m); return True,"Deleted"
        if "vm" not in st.session_state: st.session_state.vm=VM()
        vm=st.session_state.vm
        name=st.text_input("Save as")
        if st.button("Save"): st.success(vm.save(name,st.session_state.assessment)[1])
        meta=vm.list()
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
    st.write("Existing DBs:")
    for f in list_dbs():
        st.write(f.name)
