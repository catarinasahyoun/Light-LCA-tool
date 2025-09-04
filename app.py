# Easy LCA Indicator — Sign‑in first, preserved vibe, logo, DB persistence, User Guide
# ----------------------------------------------------------------------------------
# What you get (no surprises):
# • First screen = Sign‑in gate (email + optional name). Nothing else renders before that.
# • Your Tchai logo shown at top (tries ./tchai_logo.png first, falls back to /mnt/data/tchai_logo.png).
# • Database tab: ONE Excel workbook with two sheets: "Processes" and "Materials".
#   - Per‑user persistence: saved to ./data/<hash_of_email>/lca_database.xlsx.
#   - No auto‑preview unless you toggle it on.
# • Calculator tab: choose a process, quantity, unit; auto‑detects impact columns (e.g., GWP/CO2e) and computes totals.
# • User Guide tab: auto‑lists any DOCX/PDF in ./guides and renders inline (needs `mammoth` or `python-docx` for DOCX).
# • Reports tab: export your current DB to XLSX.
# • Settings: sign out + clear in‑memory cache.
#
# Paste this file as app.py, create folders `data/` and `guides/` (auto‑created if missing), and run:
#   streamlit run app.py
# ----------------------------------------------------------------------------------

import io
import re
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple, List

import pandas as pd
import streamlit as st

# =========================
# Page & simple styling
# =========================
st.set_page_config(page_title="Easy LCA Indicator", page_icon="🌿", layout="wide")

PRIMARY = "#2E7D32"  # deep green accent

st.markdown(
    f"""
    <style>
      :root {{ --brand: {PRIMARY}; }}
      .block-container {{ padding-top: 1.0rem; padding-bottom: 2.2rem; }}
      .title-row {{ display:flex; align-items:center; gap:.75rem; margin-bottom:.5rem; }}
      .title-row img {{ width:40px; height:40px; border-radius:8px; border:1px solid #cfe8cf; }}
      .title-text {{ font-size: 1.8rem; font-weight: 800; color: {PRIMARY}; }}
      .sub {{ color:#4d7c4d; margin-top:-2px; }}
      .card {{ border:1px solid rgba(15,23,42,.06); border-radius:14px; padding:14px 16px; background:#fff; }}
      .stButton>button {{ background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)!important; color:#fff!important; border:0!important; border-radius:10px!important; padding:8px 14px!important; font-weight:700!important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Paths and constants
# =========================
APP_DIR = Path.cwd()
DATA_DIR = APP_DIR / "data"
GUIDE_DIR = APP_DIR / "guides"
DATA_DIR.mkdir(exist_ok=True)
GUIDE_DIR.mkdir(exist_ok=True)

DEFAULT_DB_NAME = "lca_database.xlsx"
PROCESSES_SHEET = "Processes"
MATERIALS_SHEET = "Materials"

LOGO_PATHS = [Path("tchai_logo.png"), Path("/mnt/data/tchai_logo.png")]  # tries local first, then sandbox path

# =========================
# Auth helpers (sign‑in gate)
# =========================

def _hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def current_user() -> Optional[Dict[str, str]]:
    return st.session_state.get("user")


def require_sign_in():
    """Shows a minimal sign‑in form and stops the app until user is signed in."""
    if current_user():
        return
    st.markdown("<h2>Sign in</h2>", unsafe_allow_html=True)
    with st.form("signin_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="name@example.com")
        name = st.text_input("Name (optional)")
        submitted = st.form_submit_button("Continue →")
        if submitted:
            if email and re.match(r"^.+@.+\\..+$", email):
                st.session_state["user"] = {"email": email.strip(), "name": name.strip()}
                st.experimental_rerun()
            else:
                st.error("Please enter a valid email address.")
    st.stop()


def user_dir() -> Path:
    u = current_user()
    assert u and u.get("email"), "user must be signed in"
    d = DATA_DIR / _hash_email(u["email"]) 
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_db_path() -> Path:
    return user_dir() / DEFAULT_DB_NAME

# =========================
# Data helpers
# =========================

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


def save_uploaded_file(uploaded, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(uploaded.getbuffer())
    return out_path

# DOCX & PDF renderers (User Guide)

def docx_to_html(doc_path: Path) -> Optional[str]:
    """Return HTML for a DOCX using mammoth/python-docx if available; else None."""
    try:
        import mammoth  # type: ignore
        with open(doc_path, "rb") as f:
            result = mammoth.convert_to_html(f)
            return result.value
    except Exception:
        try:
            import docx  # type: ignore
            d = docx.Document(str(doc_path))
            return "<br/>".join(p.text for p in d.paragraphs)
        except Exception:
            return None


def embed_pdf(file_path: Path, height: int = 900):
    b64 = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>
        """,
        unsafe_allow_html=True,
    )

# =========================
# Gate: Sign‑in FIRST
# =========================
require_sign_in()
user = current_user()

# =========================
# Header + Logo
# =========================
logo_src = next((p for p in LOGO_PATHS if p.exists()), None)
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if logo_src:
        st.image(str(logo_src), use_column_width=False, width=56)
with col_title:
    st.markdown("<div class='title-text'>Easy LCA Indicator</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub'>Welcome {user.get('name') or user.get('email')}</div>", unsafe_allow_html=True)

# =========================
# Tabs
# =========================
TabCalc, TabDB, TabGuide, TabRep, TabSet = st.tabs([
    "Calculator", "Database", "User Guide", "Reports", "Settings"
])

# =========================
# Database tab (upload, persist per‑user)
# =========================
with TabDB:
    st.markdown("### Database")
    st.caption("Upload ONE Excel with sheets named 'Processes' and 'Materials'. Saved to your account.")

    uploaded = st.file_uploader("Upload/replace my database (.xlsx)", type=["xlsx"], accept_multiple_files=False)
    preview = st.toggle("Preview tables after upload", value=False)

    if uploaded is not None:
        saved = save_uploaded_file(uploaded, user_db_path())
        try:
            dfp, dfm = read_excel_db(saved)
            st.session_state["df_processes"], st.session_state["df_materials"] = dfp, dfm
            st.success("Database saved to your account.")
        except Exception as e:
            st.error(f"Failed to read Excel: {e}")

    # Lazy load from disk if session empty
    if st.session_state.get("df_processes") is None:
        p = user_db_path()
        if p.exists():
            try:
                dfp, dfm = read_excel_db(p)
                st.session_state["df_processes"], st.session_state["df_materials"] = dfp, dfm
            except Exception as e:
                st.warning(f"Saved database couldn't be read: {e}")

    if preview and st.session_state.get("df_processes") is not None:
        st.subheader("Processes (preview)")
        st.dataframe(st.session_state["df_processes"].head(30), use_container_width=True)
    if preview and st.session_state.get("df_materials") is not None:
        st.subheader("Materials (preview)")
        st.dataframe(st.session_state["df_materials"].head(30), use_container_width=True)

# =========================
# Calculator tab (clean & focused)
# =========================
with TabCalc:
    st.markdown("### LCA Calculator")

    df_proc = st.session_state.get("df_processes")
    df_mat = st.session_state.get("df_materials")

    if df_proc is None or df_mat is None:
        st.info("No database loaded yet. Go to **Database** and upload your Excel.")
    else:
        # Process name column detection
        name_col = next((c for c in ["Process", "Name", "Process Name", "process", "name"] if c in df_proc.columns), df_proc.columns[0])
        processes = df_proc[name_col].astype(str).tolist()

        c1, c2 = st.columns([2,1])
        with c1:
            selected_proc = st.selectbox("Process", processes)
        with c2:
            qty = st.number_input("Quantity", min_value=0.0, value=1.0)
        fu = st.text_input("Functional unit", value="unit")

        # Impact columns detection
        impact_cols = [c for c in df_proc.columns if re.search(r"(CO2|CO₂|GHG|GWP|impact|emission)", str(c), re.I)]
        if not impact_cols:
            st.warning("No impact column detected. Add a column such as 'GWP (kg CO2e/unit)'.")
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
                st.metric(label=f"Impact factor ({impact_col})", value=f"{factor:,.4f}")
                st.metric(label=f"Total impact for {qty:g} {fu}", value=f"{total:,.4f}")
                st.caption("Tip: Add more impact columns (energy, water, etc.) and select them here.")

# =========================
# User Guide tab (auto‑detect DOCX & PDF)
# =========================
with TabGuide:
    st.markdown("### User Guide")
    st.caption("Drop DOCX/PDF files into ./guides or upload below. They will appear automatically.")

    up = st.file_uploader("Add a guide (DOCX or PDF)", type=["docx", "pdf"], key="guide_upl")
    if up is not None:
        dest = GUIDE_DIR / up.name
        save_uploaded_file(up, dest)
        st.success(f"Saved guide: {up.name}")

    files = sorted(list(GUIDE_DIR.glob("*.docx")) + list(GUIDE_DIR.glob("*.pdf")), key=lambda p: p.name.lower())
    if not files:
        st.info("No guides found yet in ./guides")
    else:
        choice = st.selectbox("Choose a file", [p.name for p in files])
        chosen = next(p for p in files if p.name == choice)
        if chosen.suffix.lower() == ".docx":
            html = docx_to_html(chosen)
            if html:
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("Couldn't render DOCX inline (install 'mammoth' or 'python-docx').")
                st.download_button("Download DOCX", data=chosen.read_bytes(), file_name=chosen.name)
        else:
            try:
                embed_pdf(chosen, height=900)
            except Exception:
                st.download_button("Download PDF", data=chosen.read_bytes(), file_name=chosen.name)

# =========================
# Reports tab (export DB)
# =========================
with TabRep:
    st.markdown("### Reports")
    if st.session_state.get("df_processes") is None:
        st.info("Load a database to enable export.")
    else:
        with io.BytesIO() as output:
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                st.session_state["df_processes"].to_excel(writer, sheet_name="Processes", index=False)
                if st.session_state.get("df_materials") is not None:
                    st.session_state["df_materials"].to_excel(writer, sheet_name="Materials", index=False)
            data = output.getvalue()
        st.download_button("Download current DB (xlsx)", data=data, file_name="lca_current_db.xlsx")

# =========================
# Settings tab
# =========================
with TabSet:
    st.markdown("### Settings")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign out"):
            if "user" in st.session_state:
                del st.session_state["user"]
            for k in ["df_processes", "df_materials"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Signed out.")
            st.experimental_rerun()
    with col2:
        if st.button("Clear in‑memory data"):
            for k in ["df_processes", "df_materials"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.success("Cleared session data.")

# ---------------------------
# End of file
# ---------------------------
