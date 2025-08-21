# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, hashlib, secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

# =============================================================
# TCHAI — Easy LCA Indicator (full app)
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
    else:
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
# Database management (load/activate/list)
# -----------------------------
def list_databases():
    return sorted(DB_ROOT.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)

def set_active_database(path: Path):
    ACTIVE_DB_FILE.write_text(json.dumps({"path": str(path)}))
    st.success(f"Activated database: {path.name}")
    _rerun()

def get_active_database_path() -> Optional[Path]:
    if ACTIVE_DB_FILE.exists():
        try:
            data = json.loads(ACTIVE_DB_FILE.read_text())
            p = Path(data.get("path", ""))
            if p.exists():
                return p
        except Exception:
            pass
    # Fallbacks
    for candidate in [ASSETS / "Refined database.xlsx", Path("Refined database.xlsx"), Path("database.xlsx")]:
        if candidate.exists():
            return candidate
    return None

def load_active_excel() -> Optional[pd.ExcelFile]:
    p = get_active_database_path()
    if p and p.exists():
        return pd.ExcelFile(str(p))
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
    for n in names:
        if n == target:
            return n
    t = re.sub(r"\s+", "", target.lower())
    for n in names:
        if re.sub(r"\s+", "", n.lower()) == t:
            return n
    for n in names:
        if target.lower() in n.lower():
            return n
    return None

def parse_materials(df_raw: pd.DataFrame) -> dict:
    if df_raw is None or df_raw.empty:
        return {}

    df = _normalize_cols(df_raw)
    def pick(df, aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    col_name  = pick(df, ["material name", "material", "name"])
    col_co2   = pick(df, ["co2e (kg)", "co2e/kg", "co2e", "co2e per kg", "co2 (kg)", "emission factor"])
    col_rc    = pick(df, ["recycled content", "recycled content (%)", "recycled", "recycled %"])
    col_eol   = pick(df, ["eol", "end of life"])
    col_life  = pick(df, ["lifetime", "life", "lifespan", "lifetime (years)"])
    col_circ  = pick(df, ["circularity", "circ"])

    required = [col_name, col_co2]
    if any(c is None for c in required):
        return {}

    out = {}
    for _, r in df.iterrows():
        name = str(r[col_name]).strip() if pd.notna(r[col_name]) else ""
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
    def pick(df, aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    col_proc = pick(df, ["process", "step", "operation"])
    col_co2  = pick(df, ["co2e", "co2e (kg)", "co2", "emission", "factor"])
    col_unit = pick(df, ["unit", "uom"])

    if not col_proc or not col_co2:
        return {}

    out = {}
    for _, r in df.iterrows():
        name = str(r[col_proc]).strip() if pd.notna(r[col_proc]) else ""
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
# Inputs (with sheet/status panel)
# -----------------------------
if page == "Inputs":
    xls = load_active_excel()
    if not xls:
        st.error("No active database. Go to Settings → Database Manager and upload/activate one.")
        st.stop()

    auto_mat = _find_sheet(xls, "Materials")
    auto_proc = _find_sheet(xls, "Processes")

    st.subheader("Database status")
    cols = st.columns(2)
    with cols[0]:
        st.caption("Detected sheets")
        st.write(f"Materials sheet: **{auto_mat or 'not found'}**")
        st.write(f"Processes sheet: **{auto_proc or 'not found'}**")
        mat_choice = st.selectbox("Choose Materials sheet", options=xls.sheet_names,
                                  index=(xls.sheet_names.index(auto_mat) if auto_mat in xls.sheet_names else 0))
        proc_choice = st.selectbox("Choose Processes sheet", options=xls.sheet_names,
                                   index=(xls.sheet_names.index(auto_proc) if auto_proc in xls.sheet_names else 0))
    with cols[1]:
        st.caption("Preview (first 5 rows of Materials)")
        try:
            st.dataframe(pd.read_excel(xls, sheet_name=mat_choice).head(5))
        except Exception as e:
            st.warning(f"Could not preview Materials: {e}")

    try:
        mats_df = pd.read_excel(xls, sheet_name=mat_choice)
        procs_df = pd.read_excel(xls, sheet_name=proc_choice)
        st.session_state.materials = parse_materials(mats_df)
        st.session_state.processes = parse_processes(procs_df)
    except Exception as e:
        st.error(f"Could not read selected sheets: {e}")
        st.stop()

    parsed_count = len(st.session_state.materials or {})
    st.info(f"Parsed **{parsed_count}** materials from '{mat_choice}'.")
    if parsed_count == 0:
        st.warning("No materials were parsed. Check column names in your Excel. "
                   "The app accepts flexible aliases: Material name, CO2e (kg), Recycled Content, EoL, Lifetime, Circularity.")
        st.stop()

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
