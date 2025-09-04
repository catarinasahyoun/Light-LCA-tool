# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, hashlib, secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

# =============================================================
# TCHAI — Easy LCA Indicator (full app, robust Inputs)
# - Front-page Sign-in (no self-signup) with 3 pre-created users:
#   sustainability@tchai.nl / ChangeMe123!
#   jillderegt@tchai.nl     / ChangeMe123!
#   veravanbeaumont@tchai.nl/ ChangeMe123!
# - Avatar menu: change password + sign out
# - Sidebar: only the TCHAI logo + navigation (Inputs, Workspace, Settings)
# - Inputs: robust sheet detection, tolerant column parsing, preview, session override upload
# - Workspace tabs: Results, Comparison (purple), Final Summary, Report (HTML), Versions (save/load/delete)
# - Settings: Database Manager (upload .xlsx, list, activate)
# - B&W UI, purple charts; safe folder creation; st.rerun compatibility
# =============================================================

st.set_page_config(
    page_title="TCHAI — Easy LCA Indicator",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Assets (robust) + Users + DB paths
# -----------------------------
def ensure_dir(p: Path):
    """Ensure 'p' is a directory; if a file blocks the path, rename it and create the dir."""
    if p.exists() and not p.is_dir():
        backup = p.with_name(f"{p.name}_conflict_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        p.rename(backup)
    p.mkdir(parents=True, exist_ok=True)

ASSETS = Path("assets")
ensure_dir(ASSETS)

DB_ROOT = ASSETS / "databases"
ensure_dir(DB_ROOT)

USERS_FILE = ASSETS / "users.json"
ACTIVE_DB_FILE = DB_ROOT / "active.json"  # stores {"path": "<active .xlsx>"}

# -----------------------------
# Rerun helper (compat)
# -----------------------------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # pragma: no cover
        try:
            st.experimental_rerun()
        except Exception:
            pass

# -----------------------------
# Branding (logo)
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
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

# -----------------------------
# Theme (B&W + purple charts)
# -----------------------------
PURPLE = ['#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']
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
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Auth helpers & bootstrap (3 users)
# -----------------------------
def _load_users() -> dict:
    try:
        return json.loads(USERS_FILE.read_text())
    except Exception:
        return {}

def _save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))

def _hash(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode()).hexdigest()

def _initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+|_+|\.+|@", name) if p]
    return ((parts[0][0] if parts else "U") + (parts[1][0] if len(parts) > 1 else "")).upper()

def bootstrap_users_if_needed():
    users = _load_users()
    if users:
        return
    default_pw = "ChangeMe123!"
    emails = [
        "sustainability@tchai.nl",
        "jillderegt@tchai.nl",
        "veravanbeaumont@tchai.nl",
    ]
    out = {}
    for email in emails:
        salt = secrets.token_hex(8)
        out[email] = {
            "salt": salt,
            "hash": _hash(default_pw, salt),
            "created_at": datetime.now().isoformat()
        }
    _save_users(out)

bootstrap_users_if_needed()

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# -----------------------------
# Sidebar (logo only + nav)
# -----------------------------
with st.sidebar:
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px'>{logo_tag(64)}</div>",
                unsafe_allow_html=True)
    if st.session_state.auth_user:
        page = st.radio("Navigate", ["Inputs", "Workspace", "Settings"], index=0)
        st.markdown("<div class='nav-note'>Inputs are separate. Workspace contains Results, Comparison, Final Summary, Report & Versions.</div>",
                    unsafe_allow_html=True)
    else:
        page = "Sign in"

# -----------------------------
# Header (big TCHAI left, title center, avatar right)
# -----------------------------
cl, cm, cr = st.columns([0.18, 0.64, 0.18])
with cl:
    st.markdown(f"{logo_tag(86)}", unsafe_allow_html=True)
with cm:
    st.markdown("<div class='brand-title'>Easy LCA Indicator</div>", unsafe_allow_html=True)
with cr:
    if st.session_state.auth_user:
        initials = _initials(st.session_state.auth_user)
        if hasattr(st, "popover"):
            with st.popover(f"👤 {initials}"):
                st.write(f"Signed in as **{st.session_state.auth_user}**")
                st.markdown("---")
                st.subheader("Account settings")
                with st.form("change_pw_form", clear_on_submit=True):
                    cur = st.text_input("Current password", type="password")
                    new = st.text_input("New password", type="password")
                    conf = st.text_input("Confirm new password", type="password")
                    submitted = st.form_submit_button("Change password")
                if submitted:
                    users = _load_users()
                    rec = users.get(st.session_state.auth_user)
                    if not rec or _hash(cur, rec["salt"]) != rec["hash"]:
                        st.error("Current password is incorrect.")
                    elif not new or new != conf:
                        st.error("New passwords don't match.")
                    else:
                        salt = secrets.token_hex(8)
                        rec["salt"] = salt
                        rec["hash"] = _hash(new, salt)
                        users[st.session_state.auth_user] = rec
                        _save_users(users)
                        st.success("Password changed.")
                st.markdown("---")
                if st.button("Sign out"):
                    st.session_state.auth_user = None
                    _rerun()
        else:
            st.markdown(f"<div class='avatar'>{initials}</div>", unsafe_allow_html=True)
            if st.button("Sign out"):
                st.session_state.auth_user = None
                _rerun()

# -----------------------------
# Front-page Sign-in (hard gate)
# -----------------------------
if not st.session_state.auth_user:
    st.markdown("### Sign in to continue")
    t1, t2 = st.columns([0.55, 0.45])
    with t1:
        st.markdown("Use your TCHAI account email and password.")
        u = st.text_input("Email", key="login_u", placeholder="you@tchai.nl")
        p = st.text_input("Password", type="password", key="login_p")
        if st.button("Sign in"):
            users = _load_users()
            rec = users.get(u)
            if not rec:
                st.error("Unknown user.")
            elif _hash(p, rec["salt"]) != rec["hash"]:
                st.error("Wrong password.")
            else:
                st.session_state.auth_user = u
                st.success("Welcome!")
                _rerun()
    with t2:
        st.markdown("#### Need changes?")
        st.caption("User creation is disabled. Ask an admin to add a new account.")
    st.stop()

# =============================
# From here on, user is authenticated
# =============================

# -----------------------------
# Database management (robust)
# -----------------------------
def list_databases():
    return sorted((ASSETS / "databases").glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)

def set_active_database(path: Path):
    ACTIVE_DB_FILE.write_text(json.dumps({"path": str(path)}))
    st.success(f"Activated database: {path.name}")
    _rerun()

def get_active_database_path() -> Optional[Path]:
    # 1) explicit active.json
    if ACTIVE_DB_FILE.exists():
        try:
            data = json.loads(ACTIVE_DB_FILE.read_text())
            p = Path(data.get("path", ""))
            if p.exists():
                return p
        except Exception:
            pass
    # 2) newest uploaded in assets/databases/
    dbs = list_databases()
    if dbs:
        return dbs[0]
    # 3) bundled fallbacks
    for candidate in [ASSETS / "Refined database.xlsx",
                      Path("Refined database.xlsx"),
                      Path("database.xlsx")]:
        if candidate.exists():
            return candidate
    return None

def load_active_excel() -> Optional[pd.ExcelFile]:
    p = get_active_database_path()
    if p and p.exists():
        try:
            return pd.ExcelFile(str(p))
        except Exception as e:
            st.error(f"Failed to open Excel: {p.name} — {e}")
            return None
    return None

# -----------------------------
# Parsing helpers (tolerant)
# -----------------------------
def extract_number(v):
    try:
        return float(v)
    except Exception:
        s = str(v).replace(',', '.')
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group()) if m else 0.0

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c).strip()).lower() for c in df.columns]
    return df

def _find_sheet(xls: pd.ExcelFile, target: str) -> Optional[str]:
    names = xls.sheet_names
    # exact
    for n in names:
        if n == target:
            return n
    # trimmed / case-insensitive
    t = re.sub(r"\s+", "", target.lower())
    for n in names:
        if re.sub(r"\s+", "", n.lower()) == t:
            return n
    # partial
    for n in names:
        if target.lower() in n.lower():
            return n
    return None

def parse_materials(df_raw: pd.DataFrame) -> dict:
    if df_raw is None or df_raw.empty:
        return {}
    df = _normalize_cols(df_raw)

    def pick(aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    col_name = pick(["material name","material","name"])
    col_co2  = pick(["co2e (kg)","co2e/kg","co2e","co2e per kg","co2 (kg)","emission factor"])
    col_rc   = pick(["recycled content","recycled content (%)","recycled","recycled %"])
    col_eol  = pick(["eol","end of life"])
    col_life = pick(["lifetime","life","lifespan","lifetime (years)"])
    col_circ = pick(["circularity","circ"])

    if not col_name or not col_co2:
        return {}

    out = {}
    for _, r in df.iterrows():
        name = (str(r[col_name]).strip() if pd.notna(r[col_name]) else "")
        if not name:
            continue
        out[name] = {
            "CO₂e (kg)": extract_number(r[col_co2]) if pd.notna(r[col_co2]) else 0.0,
            "Recycled Content": extract_number(r[col_rc]) if col_rc and pd.notna(r.get(col_rc, None)) else 0.0,
            "EoL": str(r[col_eol]).strip() if col_eol and pd.notna(r.get(col_eol, None)) else "Unknown",
            "Lifetime": str(r[col_life]).strip() if col_life and pd.notna(r.get(col_life, None)) else "Unknown",
            "Circularity": str(r[col_circ]).strip() if col_circ and pd.notna(r.get(col_circ, None)) else "Unknown",
        }
    return out

def parse_processes(df_raw: pd.DataFrame) -> dict:
    if df_raw is None or df_raw.empty:
        return {}
    df = _normalize_cols(df_raw)

    def pick(aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    col_proc = pick(["process","step","operation"])
    col_co2  = pick(["co2e","co2e (kg)","co2","emission","factor"])
    col_unit = pick(["unit","uom"])

    if not col_proc or not col_co2:
        return {}

    out = {}
    for _, r in df.iterrows():
        name = (str(r[col_proc]).strip() if pd.notna(r[col_proc]) else "")
        if not name:
            continue
        out[name] = {
            "CO₂e": extract_number(r[col_co2]) if pd.notna(r[col_co2]) else 0.0,
            "Unit": str(r[col_unit]).strip() if col_unit and pd.notna(r.get(col_unit, None)) else "",
        }
    return out

# -----------------------------
# Session storage
# -----------------------------
if "materials" not in st.session_state: st.session_state.materials = {}
if "processes" not in st.session_state: st.session_state.processes = {}
if "assessment" not in st.session_state:
    st.session_state.assessment = {
        "lifetime_weeks": 52,
        "selected_materials": [],
        "material_masses": {},
        "processing_data": {}
    }

# -----------------------------
# Inputs (status + tolerant parsing + override uploader)
# -----------------------------
if page == "Inputs":
    # Show current active DB + optional session override
    active_path = get_active_database_path()
    st.subheader("Database status")
    c0, c1 = st.columns([0.6, 0.4])
    with c0:
        if active_path:
            st.success(f"Active database: **{active_path.name}**")
        else:
            st.error("No active database found.")
    with c1:
        st.caption("Quick override (optional)")
        override = st.file_uploader("Use a different Excel for this session", type=["xlsx"], key="override_db")

    # Decide which Excel to load
    if override is not None:
        try:
            xls = pd.ExcelFile(override)
            st.info("Using the uploaded override Excel for this session.")
        except Exception as e:
            st.error(f"Could not open the uploaded Excel: {e}")
            st.stop()
    else:
        xls = load_active_excel()

    if not xls:
        st.error("No Excel could be opened. Go to Settings → Database Manager and upload/activate one, or use the override above.")
        st.stop()

    # Sheet detection + manual choice
    auto_mat = _find_sheet(xls, "Materials")
    auto_proc = _find_sheet(xls, "Processes")

    c2, c3 = st.columns(2)
    with c2:
        st.caption("Sheets in workbook")
        st.write(", ".join(xls.sheet_names))
        mat_choice = st.selectbox("Materials sheet", options=xls.sheet_names,
                                  index=(xls.sheet_names.index(auto_mat) if auto_mat in xls.sheet_names else 0))
        proc_choice = st.selectbox("Processes sheet", options=xls.sheet_names,
                                   index=(xls.sheet_names.index(auto_proc) if auto_proc in xls.sheet_names else 0))
    with c3:
        st.caption(f"Preview of '{mat_choice}' (first 5 rows)")
        try:
            st.dataframe(pd.read_excel(xls, sheet_name=mat_choice).head(5), use_container_width=True)
        except Exception as e:
            st.warning(f"Preview error: {e}")

    # Parse selected sheets
    try:
        mats_df = pd.read_excel(xls, sheet_name=mat_choice)
        procs_df = pd.read_excel(xls, sheet_name=proc_choice)
        st.session_state.materials = parse_materials(mats_df)
        st.session_state.processes = parse_processes(procs_df)
    except Exception as e:
        st.error(f"Could not read the selected sheets: {e}")
        st.stop()

    parsed_count = len(st.session_state.materials or {})
    st.info(f"Parsed **{parsed_count}** materials from '{mat_choice}'.")
    if parsed_count == 0:
        st.warning("No materials parsed. Please check your column names. "
                   "Accepted aliases include: Material name/material/name, CO2e (kg)/CO2e, Recycled Content, EoL, Lifetime, Circularity.")
        st.stop()

    # Lifetime + Materials UI
    st.subheader("Lifetime (weeks)")
    st.session_state.assessment["lifetime_weeks"] = st.number_input(
        "", min_value=1, value=int(st.session_state.assessment.get("lifetime_weeks", 52))
    )

    st.subheader("Materials & processes")
    mats = list(st.session_state.materials.keys())
    st.session_state.assessment["selected_materials"] = st.multiselect(
        "Select materials", options=mats, 
        default=st.session_state.assessment.get("selected_materials", [])
    )

    if not st.session_state.assessment["selected_materials"]:
        st.info("Select at least one material to proceed.")
        st.stop()

    for m in st.session_state.assessment["selected_materials"]:
        st.markdown(f"### {m}")
        masses = st.session_state.assessment.setdefault("material_masses", {})
        procs_data = st.session_state.assessment.setdefault("processing_data", {})

        mass_default = float(masses.get(m, 1.0))
        masses[m] = st.number_input(f"Mass of {m} (kg)", min_value=0.0, value=mass_default, key=f"mass_{m}")

        props = st.session_state.materials[m]
        st.caption(f"CO₂e/kg: {props['CO₂e (kg)']} · Recycled %: {props['Recycled Content']} · EoL: {props['EoL']}")

        steps = procs_data.setdefault(m, [])
        n = st.number_input(f"How many processing steps for {m}?", min_value=0, max_value=10, value=len(steps), key=f"steps_{m}")
        if n < len(steps):
            steps[:] = steps[:int(n)]
        else:
            for _ in range(int(n) - len(steps)):
                steps.append({"process": "", "amount": 1.0, "co2e_per_unit": 0.0, "unit": ""})

        for i in range(int(n)):
            proc = st.selectbox(
                f"Process #{i+1}", 
                options=[''] + list(st.session_state.processes.keys()),
                index=([''] + list(st.session_state.processes.keys())).index(steps[i]['process'])
                    if steps[i]['process'] in st.session_state.processes else 0,
                key=f"proc_{m}_{i}"
            )
            if proc:
                pr = st.session_state.processes.get(proc, {})
                amt = st.number_input(
                    f"Amount for '{proc}' ({pr.get('Unit','')})", 
                    min_value=0.0, value=float(steps[i].get('amount', 1.0)), key=f"amt_{m}_{i}"
                )
                steps[i] = {"process": proc, "amount": amt, "co2e_per_unit": pr.get('CO₂e', 0.0), "unit": pr.get('Unit', '')}

# -----------------------------
# Compute results (shared)
# -----------------------------
def compute_results():
    data = st.session_state.assessment
    mats = st.session_state.materials

    total_material = 0.0
    total_process  = 0.0
    total_mass     = 0.0
    weighted       = 0.0
    eol            = {}
    cmp_rows       = []

    circ_map = {"high": 3, "medium": 2, "low": 1, "not circular": 0}

    for name in data.get('selected_materials', []):
        m = mats.get(name, {})
        mass = float(data.get('material_masses', {}).get(name, 0))
        total_mass += mass
        total_material += mass * float(m.get('CO₂e (kg)', 0))
        weighted += mass * float(m.get('Recycled Content', 0))
        eol[name] = m.get('EoL', 'Unknown')

        for s in data.get('processing_data', {}).get(name, []):
            total_process += float(s.get('amount', 0)) * float(s.get('co2e_per_unit', 0))

        cmp_rows.append({
            'Material': name,
            'CO2e per kg': float(m.get('CO₂e (kg)', 0)),
            'Recycled Content (%)': float(m.get('Recycled Content', 0)),
            'Circularity (mapped)': circ_map.get(str(m.get('Circularity','')).strip().lower(), 0),
            'Circularity (text)': m.get('Circularity', 'Unknown'),
            'Lifetime (years)': extract_number(m.get('Lifetime', 0)),
            'Lifetime (text)': m.get('Lifetime', 'Unknown'),
        })

    overall = total_material + total_process
    years = max(data.get('lifetime_weeks', 52) / 52, 1e-9)

    return {
        'total_material_co2': total_material,
        'total_process_co2': total_process,
        'overall_co2': overall,
        'weighted_recycled': (weighted / total_mass if total_mass > 0 else 0.0),
        'trees_equiv': overall / (22 * years),
        'total_trees_equiv': overall / 22,
        'lifetime_years': years,
        'eol_summary': eol,
        'comparison': cmp_rows
    }

# -----------------------------
# Workspace (tabs)
# -----------------------------
if page == "Workspace":
    if not st.session_state.assessment.get('selected_materials'):
        st.info("Go to Inputs and add at least one material.")
        st.stop()

    R = compute_results()
    tabs = st.tabs(["Results", "Comparison", "Final Summary", "Report", "Versions"])

    # Results
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total CO₂ (materials)", f"{R['total_material_co2']:.1f} kg")
        c2.metric("Total CO₂ (processes)", f"{R['total_process_co2']:.1f} kg")
        c3.metric("Weighted recycled", f"{R['weighted_recycled']:.1f}%")

    # Comparison (purple charts)
    with tabs[1]:
        df = pd.DataFrame(R['comparison'])
        if df.empty:
            st.info("No data yet.")
        else:
            def style(fig):
                fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="#fff",
                                  font=dict(color="#000", size=14),
                                  title_x=0.5, title_font_size=20)
                return fig
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(df, x="Material", y="CO2e per kg", color="Material",
                             title="CO₂e per kg", color_discrete_sequence=PURPLE)
                st.plotly_chart(style(fig), use_container_width=True)
            with c2:
                fig = px.bar(df, x="Material", y="Recycled Content (%)", color="Material",
                             title="Recycled Content (%)", color_discrete_sequence=PURPLE)
                st.plotly_chart(style(fig), use_container_width=True)
            c3, c4 = st.columns(2)
            with c3:
                fig = px.bar(df, x="Material", y="Circularity (mapped)", color="Material",
                             title="Circularity", color_discrete_sequence=PURPLE)
                fig.update_yaxes(tickmode='array', tickvals=[0,1,2,3],
                                 ticktext=['Not Circular','Low','Medium','High'])
                st.plotly_chart(style(fig), use_container_width=True)
            with c4:
                d = df.copy()
                def life_cat(x):
                    v = extract_number(x)
                    return 'Short' if v < 5 else ('Medium' if v <= 15 else 'Long')
                d['Lifetime Category'] = d['Lifetime (years)'].apply(life_cat)
                MAP = {"Short":1, "Medium":2, "Long":3}
                d['Lifetime'] = d['Lifetime Category'].map(MAP)
                fig = px.bar(d, x="Material", y="Lifetime", color="Material",
                             title="Lifetime", color_discrete_sequence=PURPLE)
                fig.update_yaxes(tickmode='array', tickvals=[1,2,3],
                                 ticktext=['Short','Medium','Long'])
                st.plotly_chart(style(fig), use_container_width=True)

    # Final Summary
    with tabs[2]:
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric'><div>Total Impact CO₂e</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric'><div>Tree Equivalent / year</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric'><div>Total Trees</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        st.markdown("#### End‑of‑Life Summary")
        for k, v in R['eol_summary'].items():
            st.write(f"• **{k}** — {v}")

    # Report (HTML only)
    with tabs[3]:
        project = st.text_input("Project name", value="Sample Project")
        notes = st.text_area("Executive notes")
        big_logo = logo_tag(100)
        html = f"""
        <!doctype html><html><head><meta charset='utf-8'><title>{project} — TCHAI Report</title>
        <style>
          body{{font-family:Arial,sans-serif;margin:24px}}
          header{{display:flex;align-items:center;gap:16px;margin-bottom:10px}}
          th,td{{border:1px solid #eee;padding:6px 8px}}
          table{{border-collapse:collapse;width:100%}}
        </style></head>
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
        st.download_button(
            "⬇️ Download HTML report",
            data=html.encode(),
            file_name=f"TCHAI_Report_{project.replace(' ','_')}.html",
            mime="text/html"
        )
        st.caption("If you prefer PDF only later, we can add server-side HTML→PDF.")

    # Versions
    with tabs[4]:
        class VM:
            def __init__(self, storage_dir: str = "lca_versions"):
                self.dir = Path(storage_dir); self.dir.mkdir(exist_ok=True)
                self.meta = self.dir / "lca_versions_metadata.json"
            def _load(self): 
                return json.loads(self.meta.read_text()) if self.meta.exists() else {}
            def _save(self, m): 
                self.meta.write_text(json.dumps(m, indent=2))
            def save(self, name, data, desc=""):
                m = self._load()
                if not name:
                    return False, "Enter a name."
                if name in m:
                    return False, "Name exists."
                fp = self.dir / f"{name}.json"
                payload = {"assessment_data": data, "timestamp": datetime.now().isoformat(), "description": desc}
                fp.write_text(json.dumps(payload))
                m[name] = {
                    "filename": fp.name,
                    "description": desc,
                    "created_at": datetime.now().isoformat(),
                    "materials_count": len(data.get('selected_materials', [])),
                    "total_co2": data.get('overall_co2', 0)
                }
                self._save(m)
                return True, "Saved."
            def list(self):
                return self._load()
            def load(self, name):
                m = self._load()
                if name not in m:
                    return None, "Not found."
                fp = self.dir / m[name]["filename"]
                if not fp.exists():
                    return None, "File missing."
                try:
                    payload = json.loads(fp.read_text())
                    return payload.get("assessment_data", {}), "Loaded."
                except Exception as e:
                    return None, f"Read error: {e}"
            def delete(self, name):
                m = self._load()
                if name not in m:
                    return False, "Not found."
                fp = self.dir / m[name]["filename"]
                if fp.exists():
                    fp.unlink()
                del m[name]
                self._save(m)
                return True, "Deleted."

        if "vm" not in st.session_state: st.session_state.vm = VM()
        vm = st.session_state.vm

        t1, t2, t3 = st.tabs(["Save", "Load", "Manage"])
        with t1:
            name = st.text_input("Version name")
            desc = st.text_area("Description (optional)")
            if st.button("💾 Save"):
                data = {**st.session_state.assessment}
                data.update(compute_results())
                ok, msg = vm.save(name, data, desc)
                st.success(msg) if ok else st.error(msg)

        with t2:
            meta = vm.list()
            if not meta:
                st.info("No versions saved yet.")
            else:
                sel = st.selectbox("Select version", list(meta.keys()))
                if st.button("📂 Load"):
                    data, msg = vm.load(sel)
                    if data:
                        st.session_state.assessment = data
                        st.success(msg)
                    else:
                        st.error(msg)

        with t3:
            meta = vm.list()
            if not meta:
                st.info("Nothing to
                st.info("Nothing to manage yet.")
            else:
                sel = st.selectbox("Select version to delete", list(meta.keys()))
                if st.button("🗑️ Delete"):
                    ok, msg = vm.delete(sel)
                    st.success(msg) if ok else st.error(msg)
