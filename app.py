import streamlit as st
import pandas as pd
import plotly.express as px
import json, re, base64, hashlib, secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from io import BytesIO

# ================================
# TCHAI — Easy LCA Indicator (v4)
# -------------------------------
# ✓ Sign-in (3 pre-created users)
# ✓ Settings → Upload & Activate a PERMANENT database (persists until changed)
# ✓ Inputs: tolerant parsing, NO Excel previews, clear process dropdowns
# ✓ Workspace: Results & Comparison → Final Summary → Report (PDF) → Versions
# ✓ User Guide: visible in sidebar, reads from assets/guides/ (with /mnt/data fallbacks)
# ✓ PDF Report: smart-filled from live inputs; DOCX fallback if PDF backend missing
# ✓ Safe folder creation (avoids FileExistsError)
# ================================

st.set_page_config(
    page_title="TCHAI — Easy LCA Indicator",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Safe dirs
# -----------------------------

def ensure_dir(p: Path):
    if p.exists() and not p.is_dir():
        backup = p.with_name(f"{p.name}_conflict_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        p.rename(backup)
    p.mkdir(parents=True, exist_ok=True)

BASE = Path.cwd()
ASSETS = BASE / "assets"; ensure_dir(ASSETS)
DB_ROOT = ASSETS / "databases"; ensure_dir(DB_ROOT)
GUIDES = ASSETS / "guides"; ensure_dir(GUIDES)
USERS_FILE = ASSETS / "users.json"
ACTIVE_DB_FILE = DB_ROOT / "active.json"  # stores {"path": "...xlsx"}

# -----------------------------
# Optional PDF/DOCX backends
# -----------------------------
REPORTLAB_OK = False
DOCX_OK = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    REPORTLAB_OK = True
except Exception:
    REPORTLAB_OK = False

try:
    from docx import Document
    DOCX_OK = True
except Exception:
    DOCX_OK = False

# -----------------------------
# Branding (logo)
# -----------------------------
LOGO_CANDIDATES = [ASSETS / "tchai_logo.png", Path("tchai_logo.png"), Path("/mnt/data/tchai_logo.png")]
_logo_bytes = None
for p in LOGO_CANDIDATES:
    if p.exists():
        try:
            _logo_bytes = p.read_bytes(); break
        except Exception:
            pass

def logo_tag(height=86):
    if not _logo_bytes:
        return "<span style='font-weight:900;font-size:28px'>TCHAI</span>"
    b64 = base64.b64encode(_logo_bytes).decode()
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

# -----------------------------
# Theme (B&W + purple)
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
# Rerun helper
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
# Auth (3 users)
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
        out[email] = {"salt": salt, "hash": _hash(default_pw, salt), "created_at": datetime.now().isoformat()}
    _save_users(out)

bootstrap_users_if_needed()
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# -----------------------------
# DB helpers (persistent)
# -----------------------------

def list_databases() -> List[Path]:
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
    dbs = list_databases()
    if dbs:
        return dbs[0]
    for candidate in [ASSETS / "Refined database.xlsx", Path("Refined database.xlsx"), Path("database.xlsx")]:
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
# Parsing helpers
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
    df.columns = [re.sub(r"\s+", " ", str(c).strip()).lower().replace("co₂","co2").replace("₂","2") for c in df.columns]
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

    def pick(aliases):
        for a in aliases:
            if a in df.columns:
                return a
        return None

    col_name = pick(["material name","material","name","material_name"])  
    col_co2  = pick(["co2e (kg)","co2e/kg","co2e","co2e per kg","co2 (kg)","emission factor","co2e factor","co2 factor"])  
    col_rc   = pick(["recycled content","recycled content (%)","recycled","recycled %","recycle %","recycled_pct"])  
    col_eol  = pick(["eol","end of life","end-of-life"])  
    col_life = pick(["lifetime","life","lifespan","lifetime (years)","lifetime years"])  
    col_circ = pick(["circularity","circ","circularity level"])  

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

    # Prefer your sheet's exact headers first, then fall back to broader aliases
    col_proc = pick(["process type","process_type","process","step","operation","process name","name"])
    col_co2  = pick(["co2e","co2e (kg)","co2","emission","factor","co2e factor","emission factor (kg)"]) 
    col_unit = pick(["unit","uom","units","measure","measurement"]) 

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
# Sidebar (logo + nav)
# -----------------------------
with st.sidebar:
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px'>{logo_tag(64)}</div>", unsafe_allow_html=True)
    if st.session_state.auth_user:
        # Make User Guide FIRST after sign-in
        page = st.radio("Navigate", ["User Guide", "Inputs", "Workspace", "Settings"], index=0)
        st.markdown("<div class='nav-note'>Workspace order: Results & Comparison → Final Summary → Report → Versions.</div>", unsafe_allow_html=True)
    else:
        page = "Sign in"

# -----------------------------
# Header (logo, title, avatar)
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
# Sign-in gate
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
# Authenticated from here
# =============================

# -----------------------------
# SETTINGS → Database Manager (PERSISTENT)
# -----------------------------
if page == "Settings":
    st.subheader("Database Manager")
    st.caption("Upload your Excel ONCE. It becomes the active database until you change it here.")

    active = get_active_database_path()
    if active:
        st.success(f"Active database: **{active.name}**")
    else:
        st.warning("No active database set.")

    up = st.file_uploader("Upload Excel (.xlsx) and activate", type=["xlsx"], key="db_upload")
    if up is not None:
        try:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = DB_ROOT / f"database_{ts}.xlsx"
            dest.write_bytes(up.read())
            set_active_database(dest)
        except Exception as e:
            st.error(f"Upload failed: {e}")

    st.markdown("### Available Databases")
    dbs = list_databases()
    if not dbs:
        st.info("No databases found. Upload one above.")
    else:
        for p in dbs:
            cols = st.columns([0.6,0.2,0.2])
            with cols[0]:
                st.write(f"**{p.name}**  ")
                st.caption(f"{datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
            with cols[1]:
                if active and p.samefile(active):
                    st.success("Active")
                else:
                    if st.button("Activate", key=f"act_{p.name}"):
                        set_active_database(p)
            with cols[2]:
                if active and p.samefile(active):
                    st.caption("(can't delete active)")
                else:
                    if st.button("🗑️ Delete", key=f"rm_{p.name}"):
                        try:
                            p.unlink(missing_ok=True)
                            st.success("Deleted.")
                            _rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

# -----------------------------
# INPUTS (no preview; robust parsing; optional per-session override)
# -----------------------------
if page == "Inputs":
    active_path = get_active_database_path()
    st.subheader("Database status")
    if active_path:
        st.success(f"Active database: **{active_path.name}**")
    else:
        st.error("No active database found. Go to Settings → Database Manager.")

    st.caption("Optional: override for THIS session only")
    override = st.file_uploader("Session override (.xlsx)", type=["xlsx"], key="override_db")

    # Decide which Excel to load
    if override is not None:
        try:
            xls = pd.ExcelFile(override)
            st.info("Using the uploaded session override.")
        except Exception as e:
            st.error(f"Could not open the uploaded Excel: {e}")
            st.stop()
    else:
        xls = load_active_excel()

    if not xls:
        st.error("No Excel could be opened. Go to Settings to upload/activate one, or use the override above.")
        st.stop()

    # Auto-detect sheets (no preview)
    auto_mat = _find_sheet(xls, "Materials") or xls.sheet_names[0]
    auto_proc = _find_sheet(xls, "Processes") or (xls.sheet_names[1] if len(xls.sheet_names)>1 else xls.sheet_names[0])

    c2, c3 = st.columns(2)
    with c2:
        mat_choice = st.selectbox("Materials sheet", options=xls.sheet_names,
                                  index=xls.sheet_names.index(auto_mat) if auto_mat in xls.sheet_names else 0)
    with c3:
        proc_choice = st.selectbox("Processes sheet", options=xls.sheet_names,
                                   index=xls.sheet_names.index(auto_proc) if auto_proc in xls.sheet_names else 0)

    # Parse selected sheets
    try:
        mats_df = pd.read_excel(xls, sheet_name=mat_choice)
        procs_df = pd.read_excel(xls, sheet_name=proc_choice)
        st.session_state.materials = parse_materials(mats_df)
        st.session_state.processes = parse_processes(procs_df)
    except Exception as e:
        st.error(f"Could not read the selected sheets: {e}")
        st.stop()

    parsed_m = len(st.session_state.materials or {})
    parsed_p = len(st.session_state.processes or {})
    st.info(f"Parsed **{parsed_m}** materials and **{parsed_p}** processes.")
    if parsed_m == 0:
        st.warning("No materials parsed. Check your columns: Material name/material/name + CO2e + (optional) Recycled/EoL/Lifetime/Circularity.")
        st.stop()
    if parsed_p == 0:
        st.warning("No processes parsed. Ensure the 'Processes' sheet has columns like Process Type + CO2e + Unit (exact headers), or use aliases such as Process/Step/Operation for the name column.")
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
            proc_options = [''] + list(st.session_state.processes.keys())
            current_proc = steps[i]['process'] if steps[i]['process'] in st.session_state.processes else ''
            idx = proc_options.index(current_proc) if current_proc in proc_options else 0
            proc = st.selectbox(
                f"Process #{i+1}", options=proc_options, index=idx, key=f"proc_{m}_{i}"
            )
            if proc:
                pr = st.session_state.processes.get(proc, {})
                amt = st.number_input(
                    f"Amount for '{proc}' ({pr.get('Unit','')})",
                    min_value=0.0, value=float(steps[i].get('amount', 1.0)), key=f"amt_{m}_{i}"
                )
                steps[i] = {"process": proc, "amount": amt, "co2e_per_unit": pr.get('CO₂e', 0.0), "unit": pr.get('Unit', '')}

# -----------------------------
# Compute results
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
# PDF / DOCX builders
# -----------------------------

def _material_rows_for_report(selected_materials: List[str], materials_dict: dict, material_masses: dict, lifetime_years: float):
    rows = []
    for m in selected_materials:
        props = materials_dict.get(m, {})
        mass = float(material_masses.get(m, 0.0))
        co2_per_kg = float(props.get("CO₂e (kg)", 0.0))
        co2_total = mass * co2_per_kg
        trees_mat = (co2_total / (22.0 * max(lifetime_years, 1e-9))) if lifetime_years else 0.0
        rows.append([
            m,
            f"{co2_total:.2f}",
            f"{float(props.get('Recycled Content', 0.0)):.0f}%",
            str(props.get("Circularity", "Unknown")),
            str(props.get("EoL", "Unknown")),
            f"{trees_mat:.1f}"
        ])
    return rows


def build_pdf_from_template(project: str, notes: str, summary: dict, selected_materials: List[str], materials_dict: dict, material_masses: dict) -> Optional[bytes]:
    if not REPORTLAB_OK:
        return None

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    H1 = styles["Heading1"]; H1.fontSize = 18
    H2 = styles["Heading2"]; H2.fontSize = 14
    P  = styles["BodyText"]; P.leading = 15

    story = []

    # Header with logo
    if _logo_bytes:
        try:
            img = RLImage(BytesIO(_logo_bytes), width=120, height=40)
            story += [img, Spacer(1, 6)]
        except Exception:
            pass

    story += [Paragraph(f"{project} — Easy LCA Report", H1), Spacer(1, 6)]

    # Intro (aligned with your template tone)
    story += [Paragraph("Introduction", H2),
              Paragraph("At Tchai we build different: within every brand space we design we try to leave a positive mark on people and planet. Our Easy LCA tool helps us see the real footprint of a concept before it’s built. With those numbers we can adjust, swap, or simplify.", P), Spacer(1, 8)]

    # Key metrics
    story += [Paragraph("Key Metrics", H2)]
    story += [Paragraph(f"Lifetime: <b>{summary['lifetime_years']:.1f} years</b> ({int(summary['lifetime_years']*52)} weeks)", P)]
    story += [Paragraph(f"Total CO₂e: <b>{summary['overall_co2']:.1f} kg</b>", P)]
    story += [Paragraph(f"Weighted recycled content: <b>{summary['weighted_recycled']:.1f}%</b>", P)]
    story += [Paragraph(f"Trees/year: <b>{summary['trees_equiv']:.1f}</b> · Total trees: <b>{summary['total_trees_equiv']:.1f}</b>", P)]
    story += [Paragraph("<i>Tree Equivalent is a communication proxy: the estimated number of trees needed to sequester the same CO₂e over your chosen lifetime (assumes ~22 kg CO₂ per tree per year).</i>", P), Spacer(1, 8)]

    if notes:
        story += [Paragraph("Executive Notes", H2), Paragraph(notes, P), Spacer(1, 8)]

    # Material Comparison Overview
    story += [Paragraph("Material Comparison Overview", H2)]
    header = ["Material", "CO₂e per Unit (kg CO₂e)", "Avg. Recycled Content", "Circularity", "End-of-Life", "Tree Equivalent*"]
    body = _material_rows_for_report(selected_materials, materials_dict, material_masses, summary["lifetime_years"])
    table = Table([header] + body, colWidths=[90, 90, 90, 80, 90, 80])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.6, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story += [table, Spacer(1, 6)]
    story += [Paragraph("*Estimated number of trees required to sequester the CO₂e emissions from one unit over the selected years.", P)]

    # End-of-Life Summary
    story += [Spacer(1, 6), Paragraph("End-of-Life Summary", H2)]
    if summary["eol_summary"]:
        bullets = "".join([f"• <b>{k}</b>: {v}<br/>" for k, v in summary["eol_summary"].items()])
        story += [Paragraph(bullets, P)]
    else:
        story += [Paragraph("—", P)]

    # Conclusion
    story += [Spacer(1, 8), Paragraph("Conclusion", H2),
              Paragraph("Not every improvement appears in a CO₂e score, and that’s okay. Each option presents different strengths and trade-offs. Use these insights to shape a smarter, more sustainable design.", P)]

    doc.build(story)
    pdf_bytes = buf.getvalue(); buf.close()
    return pdf_bytes


def build_docx_fallback(project: str, notes: str, summary: dict, selected_materials: List[str], materials_dict: dict, material_masses: dict) -> Optional[bytes]:
    if not DOCX_OK:
        return None
    doc = Document()
    doc.add_heading(f"{project} — Easy LCA Report", 0)
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph("At Tchai we build different… Our Easy LCA tool helps us see the real footprint of a concept before it’s built.")
    doc.add_heading("Key Metrics", level=1)
    doc.add_paragraph(f"Lifetime: {summary['lifetime_years']:.1f} years ({int(summary['lifetime_years']*52)} weeks)")
    doc.add_paragraph(f"Total CO₂e: {summary['overall_co2']:.1f} kg")
    doc.add_paragraph(f"Weighted recycled content: {summary['weighted_recycled']:.1f}%")
    doc.add_paragraph(f"Trees/year: {summary['trees_equiv']:.1f} · Total trees: {summary['total_trees_equiv']:.1f}")
    doc.add_paragraph("Tree Equivalent is a communication proxy: the estimated number of trees needed to sequester the same CO₂e over your chosen lifetime (assumes ~22 kg CO₂ per tree per year).")
    if notes:
        doc.add_heading("Executive Notes", level=2); doc.add_paragraph(notes)
    doc.add_heading("Material Comparison Overview", level=1)
    table = doc.add_table(rows=1, cols=6)
    hdr = table.rows[0].cells
    hdr[0].text = "Material"; hdr[1].text = "CO₂e per Unit"; hdr[2].text = "Avg. Recycled Content"; hdr[3].text = "Circularity"; hdr[4].text = "End-of-Life"; hdr[5].text = "Tree Equivalent*"
    for row in _material_rows_for_report(selected_materials, materials_dict, material_masses, summary["lifetime_years"]):
        r = table.add_row().cells
        for i, v in enumerate(row): r[i].text = str(v)
    doc.add_paragraph("*Estimated number of trees required to sequester the CO₂e emissions from one unit over the selected years.")
    doc.add_heading("End-of-Life Summary", level=1)
    if summary['eol_summary']:
        for k, v in summary['eol_summary'].items():
            doc.add_paragraph(f"• {k}: {v}")
    else:
        doc.add_paragraph("—")
    doc.add_heading("Conclusion", level=1)
    doc.add_paragraph("Not every improvement appears in a CO₂e score. Use these insights to shape a smarter, more sustainable design.")
    bio = BytesIO(); doc.save(bio); return bio.getvalue()

# -----------------------------
# WORKSPACE
# -----------------------------
if page == "Workspace":
    if not st.session_state.assessment.get('selected_materials'):
        st.info("Go to Inputs and add at least one material.")
        st.stop()

    R = compute_results()
    tabs = st.tabs(["Results & Comparison", "Final Summary", "Report", "Versions"])

    # Results & Comparison together
    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total CO₂ (materials)", f"{R['total_material_co2']:.1f} kg")
        c2.metric("Total CO₂ (processes)", f"{R['total_process_co2']:.1f} kg")
        c3.metric("Weighted recycled", f"{R['weighted_recycled']:.1f}%")

        df = pd.DataFrame(R['comparison'])
        if df.empty:
            st.info("No data yet.")
        else:
            def style(fig):
                fig.update_layout(plot_bgcolor="#fff", paper_bgcolor="#fff", font=dict(color="#000", size=14), title_x=0.5, title_font_size=20)
                return fig
            a, b = st.columns(2)
            with a:
                fig = px.bar(df, x="Material", y="CO2e per kg", color="Material", title="CO₂e per kg", color_discrete_sequence=PURPLE)
                st.plotly_chart(style(fig), use_container_width=True)
            with b:
                fig = px.bar(df, x="Material", y="Recycled Content (%)", color="Material", title="Recycled Content (%)", color_discrete_sequence=PURPLE)
                st.plotly_chart(style(fig), use_container_width=True)
            c, d = st.columns(2)
            with c:
                fig = px.bar(df, x="Material", y="Circularity (mapped)", color="Material", title="Circularity", color_discrete_sequence=PURPLE)
                fig.update_yaxes(tickmode='array', tickvals=[0,1,2,3], ticktext=['Not Circular','Low','Medium','High'])
                st.plotly_chart(style(fig), use_container_width=True)
            with d:
                g = df.copy()
                def life_cat(x):
                    v = extract_number(x)
                    return 'Short' if v < 5 else ('Medium' if v <= 15 else 'Long')
                g['Lifetime Category'] = g['Lifetime (years)'].apply(life_cat)
                MAP = {"Short":1, "Medium":2, "Long":3}
                g['Lifetime'] = g['Lifetime Category'].map(MAP)
                fig = px.bar(g, x="Material", y="Lifetime", color="Material", title="Lifetime", color_discrete_sequence=PURPLE)
                fig.update_yaxes(tickmode='array', tickvals=[1,2,3], ticktext=['Short','Medium','Long'])
                st.plotly_chart(style(fig), use_container_width=True)

    # Final Summary
    with tabs[1]:
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric'><div>Total Impact CO₂e</div><h2>{R['overall_co2']:.1f} kg</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric'><div>Tree Equivalent / year</div><h2>{R['trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric'><div>Total Trees</div><h2>{R['total_trees_equiv']:.1f}</h2></div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='margin-top:8px; font-size:0.95rem; color:#374151'>"
            "<b>Tree Equivalent</b> is a communication proxy: the estimated number of trees needed to sequester the same CO₂e over your chosen lifetime "
            "(assumes ~22 kg CO₂ per tree per year)."
            "</p>",
            unsafe_allow_html=True
        )
        st.markdown("#### End-of-Life Summary")
        for k, v in R['eol_summary'].items():
            st.write(f"• **{k}** — {v}")

    # Report (PDF with DOCX fallback)
    with tabs[2]:
        project = st.text_input("Project name", value="Sample Project")
        notes = st.text_area("Executive notes")

        pdf_bytes = build_pdf_from_template(
            project=project,
            notes=notes,
            summary={
                "lifetime_years": R["lifetime_years"],
                "overall_co2": R["overall_co2"],
                "weighted_recycled": R["weighted_recycled"],
                "trees_equiv": R["trees_equiv"],
                "total_trees_equiv": R["total_trees_equiv"],
                "eol_summary": R["eol_summary"],
            },
            selected_materials=st.session_state.assessment["selected_materials"],
            materials_dict=st.session_state.materials,
            material_masses=st.session_state.assessment["material_masses"],
        )

        if pdf_bytes:
            st.download_button("⬇️ Download PDF report (smart-filled)", data=pdf_bytes,
                               file_name=f"TCHAI_Report_{project.replace(' ','_')}.pdf", mime="application/pdf")
        else:
            st.warning("PDF backend not found (ReportLab). Offering DOCX instead.")
            docx_bytes = build_docx_fallback(
                project, notes,
                summary={
                    "lifetime_years": R["lifetime_years"],
                    "overall_co2": R["overall_co2"],
                    "weighted_recycled": R["weighted_recycled"],
                    "trees_equiv": R["trees_equiv"],
                    "total_trees_equiv": R["total_trees_equiv"],
                    "eol_summary": R["eol_summary"],
                },
                selected_materials=st.session_state.assessment["selected_materials"],
                materials_dict=st.session_state.materials,
                material_masses=st.session_state.assessment["material_masses"],
            )
            if docx_bytes:
                st.download_button("⬇️ Download DOCX report (smart-filled)", data=docx_bytes,
                                   file_name=f"TCHAI_Report_{project.replace(' ','_')}.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            else:
                st.error("Neither PDF nor DOCX export is available. Please add 'reportlab' or 'python-docx' to the environment.")

    # Versions
    with tabs[3]:
        class VM:
            def __init__(self, storage_dir: str = "lca_versions"):
                self.dir = Path(storage_dir); ensure_dir(self.dir)
                self.meta = self.dir / "lca_versions_metadata.json"
            def _load(self): return json.loads(self.meta.read_text()) if self.meta.exists() else {}
            def _save(self, m): self.meta.write_text(json.dumps(m, indent=2))
            def save(self, name, data, desc=""):
                m = self._load()
                if not name: return False, "Enter a name."
                if name in m: return False, "Name exists."
                fp = self.dir / f"{name}.json"
                payload = {"assessment_data": data, "timestamp": datetime.now().isoformat(), "description": desc}
                fp.write_text(json.dumps(payload))
                m[name] = {"filename": fp.name, "description": desc, "created_at": datetime.now().isoformat(),
                           "materials_count": len(data.get('selected_materials', [])), "total_co2": data.get('overall_co2', 0)}
                self._save(m); return True, "Saved."
            def list(self): return self._load()
            def load(self, name):
                m = self._load()
                if name not in m: return None, "Not found."
                fp = self.dir / m[name]["filename"]
                if not fp.exists(): return None, "File missing."
                try:
                    payload = json.loads(fp.read_text()); return payload.get("assessment_data", {}), "Loaded."
                except Exception as e:
                    return None, f"Read error: {e}"
            def delete(self, name):
                m = self._load()
                if name not in m: return False, "Not found."
                fp = self.dir / m[name]["filename"]
                if fp.exists(): fp.unlink()
                del m[name]; self._save(m); return True, "Deleted."

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
                st.info("Nothing to manage yet.")
            else:
                sel = st.selectbox("Select version to delete", list(meta.keys()))
                if st.button("🗑️ Delete"):
                    ok, msg = vm.delete(sel)
                    st.success(msg) if ok else st.error(msg)

# -----------------------------
# USER GUIDE (render + downloads) — FIRST after sign-in
# -----------------------------
def _find_first_existing(paths: List[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None

def _docx_to_markdown(doc_path: Path) -> str:
    """Lightweight DOCX → Markdown-ish converter for headings, bullets, paragraphs, and simple tables."""
    if not DOCX_OK:
        return ""
    from docx import Document  # local import to avoid errors when library missing
    doc = Document(str(doc_path))

    lines: List[str] = []

    # Paragraphs: headings, bullets, numbers, body
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append("")
            continue

        style = (para.style.name or "").lower()

        # Headings
        if "heading 1" in style:
            lines.append(f"# {text}")
            continue
        if "heading 2" in style:
            lines.append(f"## {text}")
            continue
        if "heading 3" in style:
            lines.append(f"### {text}")
            continue

        # Bullets / numbered
        if "list bullet" in style or "bullet" in style:
            lines.append(f"- {text}")
            continue
        if "list number" in style or "number" in style:
            lines.append(f"1. {text}")
            continue

        # Body
        lines.append(text)

    # Very simple table rendering
    for tbl in doc.tables:
        if tbl.rows:
            header_cells = [c.text.strip() for c in tbl.rows[0].cells]
            if any(h for h in header_cells):
                lines.append("")
                lines.append("| " + " | ".join(header_cells) + " |")
                lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")
                for r in tbl.rows[1:]:
                    cells = [c.text.strip() for c in r.cells]
                    lines.append("| " + " | ".join(cells) + " |")
                lines.append("")

    return "\n".join(lines).strip()
    
# ---------- User Guide (PDF) helper ----------
def render_pdf_inline(pdf_path: Path, title: str = "📘 LCA-Light Usage Overview (PDF)"):
    """
    Renders a local PDF inline using an iframe (no python-docx needed).
    """
    try:
        pdf_bytes = Path(pdf_path).read_bytes()
    except Exception as e:
        st.warning(f"Could not read PDF at {pdf_path}: {e}")
        return

    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(f"### {title}")
    html = f"""
    <iframe
        src="data:application/pdf;base64,{b64}"
        width="100%" height="900"
        style="border:none;border-radius:8px;"
    ></iframe>
    """
    st.components.v1.html(html, height=920, scrolling=True)

if page == "User Guide":
    st.subheader("User Guide")
    st.caption(
        "Files in <code>assets/guides/</code> persist. This page renders the overview and lets you download the rest.",
        help="DOCX is rendered inline below if available; PDFs are offered as downloads.",
    )

    # Candidates
    lca_light_candidates = [
        GUIDES / "LCA-Light Usage Overview.docx",
        GUIDES / "LCA-Light Usage Overview (1).docx",
        Path("/mnt/data/LCA-Light Usage Overview (1).docx"),
    ]
    text_report_candidates = [
        GUIDES / "Text_Report of the Easy LCA Tool.docx",
        GUIDES / "Text_Report of the Easy LCA Tool (1).docx",
        Path("/mnt/data/Text_Report of the Easy LCA Tool (1).docx"),
    ]
    redesign_pdf_candidates = [
        GUIDES / "LCA Tool Redesign V2.pdf",
        GUIDES / "LCA Tool Redesign V2 (1).pdf",
        Path("/mnt/data/LCA Tool Redesign V2 (1).pdf"),
    ]
    slides_pdf_candidates = [
        GUIDES / "LCA Tool.pdf",
        Path("/mnt/data/LCA Tool.pdf"),
    ]

       # 1) Render the LCA-Light Usage Overview inline (DOCX if possible, else PDF)
    st.markdown("### 📘 LCA-Light Usage Overview (inline)")
    docx_path = _find_first_existing(lca_light_candidates)
    rendered = False

    if docx_path and DOCX_OK:
        try:
            md = _docx_to_markdown(docx_path)
            if md:
                st.markdown(md)
                rendered = True
            else:
                st.info("DOCX found but produced no content. Falling back to PDF inline.")
        except Exception as e:
            st.info(f"DOCX rendering failed ({e}). Falling back to PDF inline.")

    if not rendered:
        # PDF fallback (works without python-docx)
        pdf_inline = _find_first_existing(redesign_pdf_candidates) or _find_first_existing(slides_pdf_candidates)
        if pdf_inline:
            with st.expander("📘 LCA-Light User Guide (PDF inline)", expanded=True):
                render_pdf_inline(pdf_inline, title="📘 LCA-Light Usage Overview (PDF)")
        else:
            # Nothing to render inline
            if not DOCX_OK:
                st.warning("`python-docx` not installed and no PDF found in assets/guides/. Add a PDF (e.g., 'LCA Tool Redesign V2 (1).pdf').")
            else:
                st.info("No DOCX/PDF guide found in assets/guides/ or /mnt/data/.")


    st.stop()

