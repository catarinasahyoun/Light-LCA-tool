# app.py — TCHAI Easy LCA Indicator
# Sign-in (email + password) first • Tchai logo visible on sign-in • Guides tab (DOCX/PDF)
# Keeps single Excel DB (Processes + Materials) + per-user persistence

import io, os, re, json, base64, secrets, hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="TCHAI — Easy LCA Indicator",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://docs.streamlit.io/",
        "Report a bug": "mailto:edwinsahyoun24@gmail.com",
        "About": "Light LCA Tool — refreshed UI (Sep 2025)"
    }
)

PRIMARY = "#00A67E"
PURPLE = ['#5B21B6','#6D28D9','#7C3AED','#8B5CF6','#A78BFA','#C4B5FD']

# -----------------------------
# Folders & small helpers
# -----------------------------
from pathlib import Path
from datetime import datetime

def ensure_dir(p: Path):
    # If something already exists at this path and it's not a directory,
    # move it out of the way so we can create the directory.
    if p.exists() and not p.is_dir():
        backup = p.with_name(f"{p.name}_conflict_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        p.rename(backup)
    p.mkdir(parents=True, exist_ok=True)
ASSETS = Path("assets"); ensure_dir(ASSETS)
DB_ROOT = ASSETS / "databases"; ensure_dir(DB_ROOT)
DATA_DIR = Path("data"); ensure_dir(DATA_DIR)
GUIDE_DIR = Path("guides"); ensure_dir(GUIDE_DIR)


DEFAULT_DB_NAME = "lca_database.xlsx"
PROCESSES_SHEET = "Processes"
MATERIALS_SHEET = "Materials"

def read_json(path: Path, default):
    try: return json.loads(path.read_text())
    except Exception: return default

def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))

def _rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

# -----------------------------
# Branding (logo)
# -----------------------------
def _load_logo_bytes() -> Optional[bytes]:
    for p in [ASSETS / "tchai_logo.png", Path("tchai_logo.png"), Path("/mnt/data/tchai_logo.png")]:
        if p.exists(): return p.read_bytes()
    return None

def logo_tag(height=86):
    b = _load_logo_bytes()
    if not b:
        return "<span style='font-weight:900;font-size:28px'>TCHAI</span>"
    b64 = base64.b64encode(b).decode()
    return f"<img src='data:image/png;base64,{b64}' alt='TCHAI' style='height:{height}px'/>"

st.markdown(f"""
<style>
:root {{ --brand: {PRIMARY}; }}
.block-container {{ padding-top: 1.0rem; padding-bottom: 2.2rem; }}
.card {{ border:1px solid rgba(15,23,42,.08); border-radius:14px; padding:14px 16px; background:#fff; }}
.stButton>button {{ background: var(--brand)!important; color:#fff!important; border:0!important; border-radius:10px!important; padding:8px 14px!important; font-weight:700!important; }}
.center {{ display:flex; align-items:center; justify-content:center; min-height: 68vh; }}
.panel {{ max-width: 560px; width:100%; background:#fff; border:1px solid rgba(15,23,42,.08); border-radius:16px; padding:22px; box-shadow: 0 10px 28px rgba(0,0,0,.08); }}
.brand-title {{ font-weight:900; font-size:26px; text-align:center; }}
.small-muted {{ font-size:.85rem; color:#64748b; }}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Users & auth (password-based)
# -----------------------------
def _hash(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode()).hexdigest()

def _load_users() -> dict:
    return read_json(USERS_FILE, {})

def _save_users(users: dict):
    write_json(USERS_FILE, users)

def bootstrap_users_if_needed():
    users = _load_users()
    if users: return
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

def _initials(email: str) -> str:
    parts = [p for p in re.split(r"\s+|_+|\.+|@", email) if p]
    return ((parts[0][0] if parts else "U") + (parts[1][0] if len(parts) > 1 else "")).upper()

# -----------------------------
# Per-user DB location
# -----------------------------
def _hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]

def current_user_folder(email: str) -> Path:
    d = DATA_DIR / _hash_email(email)
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_user_db_path(email: str) -> Optional[Path]:
    p = current_user_folder(email) / DEFAULT_DB_NAME
    return p if p.exists() else None

def save_uploaded_file(uploaded, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(uploaded.getbuffer())
    return out_path

# -----------------------------
# Sign-in gate (logo visible)
# -----------------------------
def sign_in_gate():
    if st.session_state.auth_user:
        return
    # full-screen centered with logo
    st.markdown("<div class='center'><div class='panel'>", unsafe_allow_html=True)
    st.markdown(f"<div style='display:flex;justify-content:center;margin-bottom:10px'>{logo_tag(72)}</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-title'>Easy LCA Indicator</div>", unsafe_allow_html=True)
    st.markdown("<p class='small-muted' style='text-align:center'>Sign in with your TCHAI account</p>", unsafe_allow_html=True)

    with st.form("signin_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@tchai.nl")
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        users = _load_users()
        rec = users.get(email)
        if not rec:
            st.error("Unknown user.")
        elif _hash(pw, rec["salt"]) != rec["hash"]:
            st.error("Wrong password.")
        else:
            st.session_state.auth_user = email
            st.success("Welcome!")
            st.markdown("</div></div>", unsafe_allow_html=True)
            _rerun()
            st.stop()

    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

sign_in_gate()  # <- blocks until signed in
email = st.session_state.auth_user

# -----------------------------
# Header with logo + user
# -----------------------------
cl, cm, cr = st.columns([0.18, 0.64, 0.18])
with cl: st.markdown(f"{logo_tag(86)}", unsafe_allow_html=True)
with cm: st.markdown("<div class='brand-title'>Easy LCA Indicator</div>", unsafe_allow_html=True)
with cr:
    initials = _initials(email)
    if hasattr(st, "popover"):
        with st.popover(f"👤 {initials}"):
            st.write(f"Signed in as **{email}**")
            st.markdown("---")
            st.subheader("Change password")
            with st.form("change_pw_form", clear_on_submit=True):
                cur = st.text_input("Current password", type="password")
                new = st.text_input("New password", type="password")
                conf = st.text_input("Confirm new password", type="password")
                submitted = st.form_submit_button("Update password")
            if submitted:
                users = _load_users()
                rec = users.get(email)
                if not rec or _hash(cur, rec["salt"]) != rec["hash"]:
                    st.error("Current password is incorrect.")
                elif not new or new != conf:
                    st.error("New passwords don't match.")
                else:
                    salt = secrets.token_hex(8)
                    rec["salt"] = salt
                    rec["hash"] = _hash(new, salt)
                    users[email] = rec
                    _save_users(users)
                    st.success("Password changed.")
            st.markdown("---")
            if st.button("Sign out"):
                st.session_state.auth_user = None
                _rerun()

# -----------------------------
# Tabs
# -----------------------------
Tabs = st.tabs(["Dashboard", "LCA Calculator", "Database", "Reports", "User Guide", "Settings"])

# -----------------------------
# Excel IO
# -----------------------------
def read_excel_db(path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    xl = pd.ExcelFile(path)
    if PROCESSES_SHEET not in xl.sheet_names:
        raise ValueError(f"Missing '{PROCESSES_SHEET}' sheet in {path.name}")
    if MATERIALS_SHEET not in xl.sheet_names:
        raise ValueError(f"Missing '{MATERIALS_SHEET}' sheet in {path.name}")
    df_proc = xl.parse(PROCESSES_SHEET).fillna(0)
    df_mat = xl.parse(MATERIALS_SHEET).fillna(0)
    df_proc.columns = [str(c).strip() for c in df_proc.columns]
    df_mat.columns = [str(c).strip() for c in df_mat.columns]
    return df_proc, df_mat

# cache in session
if "df_processes" not in st.session_state: st.session_state.df_processes = None
if "df_materials" not in st.session_state: st.session_state.df_materials = None

# -----------------------------
# Dashboard
# -----------------------------
with Tabs[0]:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Databases uploaded**")
        st.markdown(f"<h2>{len(list(DATA_DIR.rglob(DEFAULT_DB_NAME)))}</h2>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Signed-in user**")
        st.markdown(f"<h2>{email}</h2>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Guide detected**")
        has_any_guide = any(p.exists() for p in GUIDE_DIR.glob("*"))
        st.markdown(f"<h2>{'Yes' if has_any_guide else 'No'}</h2>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# LCA Calculator
# -----------------------------
with Tabs[1]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Calculator")
    df_proc = st.session_state.df_processes
    df_mat = st.session_state.df_materials

    # try load per-user DB if not in memory
    if (df_proc is None or df_mat is None) and get_user_db_path(email):
        try:
            df_proc, df_mat = read_excel_db(get_user_db_path(email))
            st.session_state.df_processes, st.session_state.df_materials = df_proc, df_mat
        except Exception as e:
            st.warning(f"Could not load your saved DB: {e}")

    if df_proc is None or df_mat is None:
        st.info("No database loaded yet. Upload an Excel workbook first in the **Database** tab.")
    else:
        # choose process
        name_col = next((c for c in ["Process","Name","Process Name","process","name"] if c in df_proc.columns), df_proc.columns[0])
        processes = df_proc[name_col].astype(str).tolist()
        c1, c2 = st.columns([2,1])
        with c1:
            selected_proc = st.selectbox("Select a process", processes)
        with c2:
            qty = st.number_input("Quantity", min_value=0.0, value=1.0)
        fu = st.text_input("Functional unit (e.g., kg, unit)", value="unit")

        impact_cols = [c for c in df_proc.columns if re.search(r"(CO2|CO₂|GHG|GWP|impact|emission)", str(c), re.I)]
        if not impact_cols:
            st.warning("No emission/impact columns detected in Processes sheet. Add a column like 'GWP (kg CO2e/unit)'.")
        else:
            impact_col = st.selectbox("Impact column", impact_cols)
            row = df_proc[df_proc[name_col].astype(str) == str(selected_proc)]
            if row.empty:
                st.error("Selected process not found.")
            else:
                try:
                    factor = float(row.iloc[0][impact_col]) if pd.notna(row.iloc[0][impact_col]) else 0.0
                except Exception:
                    factor = 0.0
                total = qty * factor
                c1, c2 = st.columns(2)
                with c1: st.metric(label=f"Impact factor ({impact_col})", value=f"{factor:,.4f}")
                with c2: st.metric(label=f"Total impact for {qty:g} {fu}", value=f"{total:,.4f}")
                st.caption("Tip: Add more impact columns (e.g., water, energy) and pick them here.")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Database (upload + persist per user)
# -----------------------------
with Tabs[2]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Database (single Excel with `Processes` & `Materials` sheets)")
    uploaded = st.file_uploader("Upload/replace your Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False)
    preview = st.toggle("Preview tables after upload", value=False)

    if uploaded is not None:
        out_path = current_user_folder(email) / DEFAULT_DB_NAME
        saved_path = save_uploaded_file(uploaded, out_path)
        st.success(f"Saved database for **{email}**.")
        try:
            df_proc, df_mat = read_excel_db(saved_path)
            st.session_state.df_processes, st.session_state.df_materials = df_proc, df_mat
        except Exception as e:
            st.error(f"Failed to read Excel: {e}")

    if preview and st.session_state.df_processes is not None:
        st.subheader("Processes (preview)")
        st.dataframe(st.session_state.df_processes.head(30), use_container_width=True)
    if preview and st.session_state.df_materials is not None:
        st.subheader("Materials (preview)")
        st.dataframe(st.session_state.df_materials.head(30), use_container_width=True)

    if st.button("Load my saved database"):
        p = get_user_db_path(email)
        if p:
            try:
                df_proc, df_mat = read_excel_db(p)
                st.session_state.df_processes, st.session_state.df_materials = df_proc, df_mat
                st.success("Database loaded from disk.")
            except Exception as e:
                st.error(f"Failed to read saved Excel: {e}")
        else:
            st.info("No saved database found yet.")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Reports (export current DB)
# -----------------------------
with Tabs[3]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Reports")
    if st.session_state.df_processes is None:
        st.info("Load a database to enable export.")
    else:
        with io.BytesIO() as output:
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                st.session_state.df_processes.to_excel(writer, sheet_name="Processes", index=False)
                if st.session_state.df_materials is not None:
                    st.session_state.df_materials.to_excel(writer, sheet_name="Materials", index=False)
            data = output.getvalue()
        st.download_button("Download current DB (xlsx)", data=data, file_name="lca_current_db.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# User Guide (DOCX/PDF)
# -----------------------------
def try_import_mammoth():
    try:
        import mammoth  # type: ignore
        return mammoth
    except Exception:
        return None

def try_import_docx():
    try:
        import docx  # type: ignore
        return docx
    except Exception:
        return None

def docx_to_html(doc_path: Path) -> Optional[str]:
    mammoth = try_import_mammoth()
    if mammoth:
        with open(doc_path, "rb") as f:
            result = mammoth.convert_to_html(f)
            return result.value
    docx = try_import_docx()
    if docx:
        d = docx.Document(str(doc_path))
        return "<br/>".join(p.text for p in d.paragraphs)
    return None

def embed_pdf(file_path: Path, height: int = 900):
    b64 = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>',
        unsafe_allow_html=True
    )

with Tabs[4]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### User Guide")
    st.caption("Drop DOCX/PDF files into the `guides/` folder (or upload below).")

    up = st.file_uploader("Add/replace a guide (DOCX or PDF)", type=["docx","pdf"], key="guide_upl")
    if up is not None:
        dest = GUIDE_DIR / up.name
        save_uploaded_file(up, dest)
        st.success(f"Saved guide: {up.name}")

    files = sorted(list(GUIDE_DIR.glob("*.docx")) + list(GUIDE_DIR.glob("*.pdf")), key=lambda p: p.name.lower())
    if not files:
        st.info("No guides found yet in `guides/`.")
    else:
        choice = st.selectbox("Choose a document to view", [p.name for p in files])
        chosen = next(p for p in files if p.name == choice)
        if chosen.suffix.lower() == ".docx":
            html = docx_to_html(chosen)
            if html: st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("Install `mammoth` or `python-docx` for inline DOCX.")
                st.download_button("Download DOCX", data=chosen.read_bytes(), file_name=chosen.name)
        else:
            try:
                embed_pdf(chosen, height=900)
            except Exception:
                st.download_button("Download PDF", data=chosen.read_bytes(), file_name=chosen.name)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# Settings
# -----------------------------
with Tabs[5]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Settings & Maintenance")

    if st.button("Clear in-memory data (current session)"):
        for k in ["df_processes", "df_materials"]:
            if k in st.session_state: del st.session_state[k]
        st.success("Cleared session data.")

    user_dir = current_user_folder(email)
    if (user_dir / DEFAULT_DB_NAME).exists():
        if st.button("Delete my saved database"):
            try:
                (user_dir / DEFAULT_DB_NAME).unlink(missing_ok=True)
                st.success("Deleted your saved database.")
            except Exception as e:
                st.error(f"Couldn't delete: {e}")
    else:
        st.caption("No saved database yet.")

    st.markdown("</div>", unsafe_allow_html=True)

