import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, os, hashlib, secrets
from datetime import datetime
from pathlib import Path

# =============================================================
# TCHAI — Easy LCA Indicator (Ergonomic Revamp)
# =============================================================
# What this revision implements from your latest notes:
# - Sign-in on the **front page** (full-screen). App is fully gated: you cannot use anything until logged in.
# - After login, **sign-in controls are hidden**. Instead, a **user avatar** appears top-right; clicking it opens a menu with
#   "My account" (placeholder) and "Sign out". (Uses st.popover if available; otherwise shows buttons inline.)
# - Left sidebar: **only the TCHAI logo** (no title). Sidebar keeps the page navigator.
# - Main header: **TCHAI much bigger** at top-left; app title centered.
# - Navigation: **Inputs alone** in the sidebar. All other workflow pages are grouped under one **Workspace** page
#   with tabs: Results, Comparison, Final Summary, Report, Versions.
# - Colors: **Black & White UI**, charts are **purple** (PDF-like).
# - Report download: **single format (HTML)**, bigger TCHAI in header, removed duplicate "Easy LCA Indicator" text.
# - General ergonomics: consistent spacing, validation, clearer empty states.
# =============================================================

st.set_page_config(page_title="TCHAI — Easy LCA Indicator", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

# -----------------------------
# Branding & assets
# -----------------------------
ASSETS = Path("assets"); ASSETS.mkdir(exist_ok=True)
LOGO_PATHS = [ASSETS/"tchai_logo.png", Path("tchai_logo.png")]
logo_bytes = None
for p in LOGO_PATHS:
    if p.exists():
        logo_bytes = p.read_bytes(); break

def logo_tag(height=72):
    if not logo_bytes:
        return "<span style='font-weight:900;font-size:28px'>TCHAI</span>"
    b64 = base64.b64encode(logo_bytes).decode()
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

PURPLE = ['#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']

st.markdown(
    """
    <style>
      .stApp{background:#fff;color:#000}
      .bw-card{border:1px solid #e5e7eb;border-radius:14px;padding:18px;background:#fff}
      .metric{border:1px solid #111;border-radius:12px;padding:14px;text-align:center}
      .header-wrap{display:flex;align-items:center;gap:14px}
      .brand-title{font-weight:900;font-size:26px;text-align:center}
      .nav-note{color:#6b7280;font-size:12px}
      /* inputs */
      .stSelectbox div[data-baseweb="select"], .stNumberInput input{border:1px solid #111}
      /* avatar */
      .avatar{width:36px;height:36px;border-radius:9999px;background:#111;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Auth (front page)
# -----------------------------
USERS_FILE = ASSETS/"users.json"
if not USERS_FILE.exists(): USERS_FILE.write_text(json.dumps({}))

def _load_users():
    try: return json.loads(USERS_FILE.read_text())
    except Exception: return {}

def _save_users(data): USERS_FILE.write_text(json.dumps(data, indent=2))

def _hash(pw, salt): return hashlib.sha256((salt+pw).encode()).hexdigest()

def _initials(name: str) -> str:
    parts=[p for p in re.split(r"\s+|_+|\.+|@", name) if p]
    s=(parts[0][0] if parts else "U")+(parts[1][0] if len(parts)>1 else "")
    return s.upper()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# -----------------------------
# Sidebar (logo only + navigator)
# -----------------------------
with st.sidebar:
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px'>{logo_tag(56)}</div>", unsafe_allow_html=True)
    if st.session_state.auth_user:
        page = st.radio("Navigate", ["Inputs","Workspace","Settings"], index=0)
        st.markdown("<div class='nav-note'>Inputs are separate. Workspace contains Results, Comparison, Summary, Report & Versions.</div>", unsafe_allow_html=True)
    else:
        page = "Sign in"

# -----------------------------
# Header (big TCHAI on the left, centered title, user avatar on right)
# -----------------------------
cl, cm, cr = st.columns([0.18,0.64,0.18])
with cl: st.markdown(f"<div class='header-wrap'>{logo_tag(80)}</div>", unsafe_allow_html=True)
with cm: st.markdown("<div class='brand-title'>Easy LCA Indicator</div>", unsafe_allow_html=True)
with cr:
    if st.session_state.auth_user:
        initials = _initials(st.session_state.auth_user)
        try:
            pop = st.popover(" ", use_container_width=False)
            st.markdown(f"<div class='avatar'>{initials}</div>", unsafe_allow_html=True)
            with pop:
                st.write(f"Signed in as **{st.session_state.auth_user}**")
                st.button("My account (coming soon)")
                if st.button("Sign out"):
                    st.session_state.auth_user=None
                    st.experimental_rerun()
        except Exception:
            # Fallback if st.popover not available
            st.markdown(f"<div class='avatar'>{initials}</div>", unsafe_allow_html=True)
            if st.button("Sign out"):
                st.session_state.auth_user=None
                st.experimental_rerun()

# -----------------------------
# Front-page Sign-in (block entire app until logged in)
# -----------------------------
if not st.session_state.auth_user:
    st.markdown("### Sign in to continue")
    t1, t2 = st.columns([0.55,0.45])
    with t1:
        st.markdown("<div class='bw-card'>Enter your credentials or create a new account.</div>", unsafe_allow_html=True)
        u = st.text_input("Email or username", key="login_u", placeholder="your.name@tchai.com")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Sign in", use_container_width=False):
            users = _load_users(); rec = users.get(u)
            if not rec: st.error("User not found.")
            elif _hash(p, rec["salt"]) != rec["hash"]: st.error("Wrong password.")
            else:
                st.session_state.auth_user = u
                st.success("Welcome back!")
                st.experimental_rerun()
    with t2:
        st.markdown("#### Create account")
        nu = st.text_input("New username", key="new_u")
        np = st.text_input("New password", type="password", key="new_p")
        if st.button("Create account"):
            users = _load_users()
            if not nu or not np:
                st.error("Enter username and password.")
            elif nu in users:
                st.error("Account already exists.")
            else:
                salt = secrets.token_hex(8)
                users[nu] = {"salt": salt, "hash": _hash(np, salt), "created_at": datetime.now().isoformat()}
                _save_users(users)
                st.success("Account created. You can sign in now.")
    st.stop()

# =============================
# From here on, user is authenticated
# =============================

# ----------- Helpers & parsing -----------

def extract_number(v):
    try: return float(v)
    except Exception:
        s=str(v).replace(',', '.')
        m=re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def parse_materials(df: pd.DataFrame):
    cols=["Material name","CO2e (kg)","Recycled Content","EoL","Lifetime","Comment","Circularity","Alternative Material"]
    df.columns=[str(c).strip() for c in df.columns]
    for c in cols:
        if c not in df.columns:
            st.error(f"Missing column in Materials: '{c}'"); return {}
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

def parse_processes(df: pd.DataFrame):
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

# ----------- Session storage -----------
if "materials" not in st.session_state: st.session_state.materials = {}
if "processes" not in st.session_state: st.session_state.processes = {}
if "assessment" not in st.session_state:
    st.session_state.assessment = {"lifetime_weeks":52,"selected_materials":[],"material_masses":{},"processing_data":{}}

# ----------- Inputs page -----------
if page == "Inputs":
    st.subheader("Upload Excel database")
    up = st.file_uploader("Excel (.xlsx) with 'Materials' and 'Processes' sheets", type=["xlsx"])
    if up is not None:
        xls = pd.ExcelFile(up)
        st.session_state.materials = parse_materials(pd.read_excel(xls, sheet_name="Materials"))
        st.session_state.processes = parse_processes(pd.read_excel(xls, sheet_name="Processes"))
        if st.session_state.materials: st.success("Database loaded.")
    elif not st.session_state.materials:
        # fallback bundled
        for candidate in [Path("Refined database.xlsx"), Path("database.xlsx")]:
            if candidate.exists():
                xls = pd.ExcelFile(candidate)
                st.session_state.materials = parse_materials(pd.read_excel(xls, sheet_name="Materials"))
                st.session_state.processes = parse_processes(pd.read_excel(xls, sheet_name="Processes"))
                st.info(f"Using bundled: {candidate.name}")
                break
        if not st.session_state.materials:
            st.stop()

    st.subheader("Lifetime (weeks)")
    st.session_state.assessment["lifetime_weeks"] = st.number_input("", min_value=1, value=int(st.session_state.assessment.get("lifetime_weeks",52)))

    st.subheader("Materials & processes")
    mats = list(st.session_state.materials.keys())
    st.session_state.assessment["selected_materials"] = st.multiselect("Select materials", options=mats, default=st.session_state.assessment.get("selected_materials", []))

    if not st.session_state.assessment["selected_materials"]:
        st.info("Select at least one material to proceed."); st.stop()

    for m in st.session_state.assessment["selected_materials"]:
        st.markdown(f"### {m}")
        masses = st.session_state.assessment.setdefault("material_masses", {})
        procs_data = st.session_state.assessment.setdefault("processing_data", {})
        mass_default = float(masses.get(m, 1.0))
        masses[m] = st.number_input(f"Mass of {m} (kg)", min_value=0.0, value=mass_default, key=f"mass_{m}")
        props = st.session_state.materials[m]
        st.caption(f"CO₂e/kg: {props['CO₂e (kg)']} · Recycled %: {props['Recycled Content']} · EoL: {props['EoL']}")
        steps = procs_data.setdefault(m, [])
        n = st.number_input(f"How many processing steps for {m}?", min_value=0, max_value=10, value=len(steps))
        if n < len(steps): steps[:] = steps[:int(n)]
        else:
            for _ in range(int(n)-len(steps)):
                steps.append({"process":"","amount":1.0,"co2e_per_unit":0.0,"unit":""})
        for i in range(int(n)):
            proc = st.selectbox(f"Process #{i+1}", options=['']+list(st.session_state.processes.keys()), index=(['']+list(st.session_state.processes.keys())).index(steps[i]['process']) if steps[i]['process'] in st.session_state.processes else 0, key=f"proc_{m}_{i}")
            if proc:
                pr = st.session_state.processes.get(proc, {})
                amt = st.number_input(f"Amount for '{proc}' ({pr.get('Unit','')})", min_value=0.0, value=float(steps[i].get('amount',1.0)), key=f"amt_{m}_{i}")
                steps[i] = {"process":proc, "amount":amt, "co2e_per_unit":pr.get('CO₂e',0.0), "unit":pr.get('Unit','')}

# ----------- Compute results -----------

def compute_results():
    data = st.session_state.assessment
    mats = st.session_state.materials
    total_material=total_process=total_mass=weighted=0.0
    eol={}; cmp=[]
    circ_map={"High":3,"Medium":2,"Low":1,"Not Circular":0}
    for name in data.get('selected_materials', []):
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

# ----------- Workspace page (grouped) -----------
if page == "Workspace":
    if not st.session_state.assessment.get('selected_materials'):
        st.info("Go to Inputs and add at least one material.")
        st.stop()
    R = compute_results()
    tabs = st.tabs(["Results","Comparison","Final Summary","Report","Versions"])

    # Results
    with tabs[0]:
        c1,c2,c3 = st.columns(3)
        c1.metric("Total CO₂ (materials)", f"{R['total_material_co2']:.1f} kg")
        c2.metric("Total CO₂ (processes)", f"{R['total_process_co2']:.1f} kg")
        c3.metric("Weighted recycled", f"{R['weighted_recycled']:.1f}%")

    # Comparison visuals (purple, centered titles)
    with tabs[1]:
        df=pd.DataFrame(R['comparison'])
        if df.empty: st.info("No data yet.")
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

    # Final Summary
    with tabs[2]:
        m1,m2,m3 = st.columns(3)
        m1.markdown(f"<div class='metric'><div>Total Impact CO₂e</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric'><div>Tree Equivalent / year</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric'><div>Total Trees</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        st.markdown("#### End‑of‑Life Summary")
        for k,v in R['eol_summary'].items(): st.write(f"• **{k}** — {v}")

    # Report (HTML only; bigger TCHAI; no duplicate title)
    with tabs[3]:
        project = st.text_input("Project name", value="Sample Project")
        notes = st.text_area("Executive notes")
        big_logo = logo_tag(88)
        html=f"""
        <!doctype html><html><head><meta charset='utf-8'><title>{project} — TCHAI Report</title>
        <style>body{{font-family:Arial,sans-serif;margin:24px}} header{{display:flex;align-items:center;gap:16px;margin-bottom:10px}} th,td{{border:1px solid #eee;padding:6px 8px}} table{{border-collapse:collapse;width:100%}}</style></head>
        <body>
          <header>{big_logo}</header>
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
        st.download_button("⬇️ Download HTML report", data=html.encode(), file_name=f"TCHAI_Report_{project.replace(' ','_')}.html", mime="text/html")
        st.caption("If you later want PDF, we can render this HTML to PDF server-side.")

    # Versions
    with tabs[4]:
        class VM:
            def __init__(self, storage_dir: str = "lca_versions"):
                self.dir = Path(storage_dir); self.dir.mkdir(exist_ok=True)
                self.meta = self.dir/"lca_versions_metadata.json"
            def _load(self): return json.loads(self.meta.read_text()) if self.meta.exists() else {}
            def _save(self, m): self.meta.write_text(json.dumps(m, indent=2))
            def save(self, name, data, desc=""):
                m=self._load();
                if not name: return False, "Enter a name."
                if name in m: return False, "Name exists."
                fp=self.dir/f"{name}.json"; fp.write_text(json.dumps({"assessment_data":data,"timestamp":datetime.now().isoformat(),"description":desc}))
                m[name]={"filename":fp.name,"description":desc,"created_at":datetime.now().isoformat(),"materials_count":len(data.get('selected_materials',[])),"total_co2":data.get('overall_co2',0)}
                self._save(m); return True, "Saved."
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
        if "vm" not in st.session_state: st.session_state.vm = VM()
        vm = st.session_state.vm
        t1,t2,t3 = st.tabs(["Save","Load","Manage"])
        with t1:
            name = st.text_input("Version name")
            desc = st.text_area("Description (optional)")
            if st.button("💾 Save"): 
                data = {**st.session_state.assessment}
                data.update(R)
                ok,msg = vm.save(name, data, desc); st.success(msg) if ok else st.error(msg)
        with t2:
            meta = vm.list()
            if not meta: st.info("No versions saved yet.")
            else:
                sel = st.selectbox("Select version", list(meta.keys()))
                if st.button("📂 Load"):
                    data,msg = vm.load(sel)
                    if data:
                        st.session_state.assessment = data
                        st.success(msg)
                    else: st.error(msg)
        with t3:
            meta = vm.list()
            if not meta: st.info("Nothing to manage.")
            else:
                sel = st.selectbox("Delete version", list(meta.keys()))
                if st.button("🗑️ Delete", type="secondary"):
                    ok,msg = vm.delete(sel); st.success(msg) if ok else st.error(msg)

# ----------- Settings page (logo upload only) -----------
if page == "Settings":
    st.subheader("Branding")
    up = st.file_uploader("Upload TCHAI logo (PNG)", type=["png"])
    if up is not None:
        data = up.read(); (ASSETS/"tchai_logo.png").write_bytes(data)
        st.success("Logo saved to assets/tchai_logo.png. Reload to apply.")
        st.image(data, caption="Preview", width=260)
