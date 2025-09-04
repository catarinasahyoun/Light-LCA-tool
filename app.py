# Light LCA Tool — sign‑in first, simple UI, dynamic User Guide
# ---------------------------------------------------------------
# What’s new in this version
# - The very first screen is a **Sign in** form (email + optional name). Nothing else shows until you sign in.
# - Clean, minimal layout with 5 tabs: Calculator, Database, User Guide, Reports, Settings.
# - Per‑user database persistence: each user’s Excel DB is saved under ./data/<hash_of_email>/lca_database.xlsx.
# - User Guide tab now lists **all** DOCX/PDF files in ./guides automatically (no fixed filenames).
# - Optional preview toggle for raw tables.
#
# Drop this in as app.py and run:  streamlit run app.py
# ---------------------------------------------------------------

import io
import re
import base64
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Dict, List

import pandas as pd
import streamlit as st

# ---------- Basic page setup ----------
st.set_page_config(
    page_title="Light LCA Tool",
    page_icon="🌱",
    layout="wide",
)

PRIMARY = "#00A67E"

st.markdown(
    f"""
    <style>
    :root {{ --brand: {PRIMARY}; }}
    .block-container {{ padding-top: 1.4rem; padding-bottom: 2.2rem; }}
    .h1 {{ font-size: 1.8rem; font-weight: 800; margin-bottom: .25rem; }}
    .sub {{ color: #64748b; margin-bottom: 1.1rem; }}
    .card {{ border: 1px solid rgba(15,23,42,.06); border-radius: 14px; padding: 14px 16px; }}
    .stButton>button {{ background: var(--brand)!important; color: #fff!important; border: 0!important; border-radius: 10px!important; }}
    .muted {{ color: #6b7280; font-size: .9rem; }}
    .center {{ display: flex; align-items: center; justify-content: center; height: 72vh; }}
    .panel {{ max-width: 520px; width: 100%; border: 1px solid rgba(15,23,42,.08); border-radius: 16px; padding: 20px; box-shadow: 0 6px 20px rgba(0,0,0,.05); }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Paths ----------
APP_DIR = Path.cwd()
DATA_DIR = APP_DIR / "data"
GUIDE_DIR = APP_DIR / "guides"
DATA_DIR.mkdir(exist_ok=True)
GUIDE_DIR.mkdir(exist_ok=True)

DEFAULT_DB_NAME = "lca_database.xlsx"
PROCESSES_SHEET = "Processes"
MATERIALS_SHEET = "Materials"

# ---------- Helpers ----------

def _hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def current_user() -> Optional[Dict[str, str]]:
    return st.session_state.get("user")


def require_sign_in():
    u = current_user()
    if u:
        return
    # Show a centered sign-in panel and stop execution
    st.markdown("<div class='center'>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='h1'>🌿 Light LCA Tool</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub'>Please sign in to continue.</div>", unsafe_allow_html=True)
        email = st.text_input("Email", key="email_input", placeholder="name@example.com")
        name = st.text_input("Name (optional)", key="name_input")
        colA, colB = st.columns([1,4])
        with colA:
            go = st.button("Continue")
        with colB:
            st.write("")
        if go:
            if email and re.match(r"^.+@.+\..+$", email):
                st.session_state["user"] = {"email": email.strip(), "name": name.strip()}
                st.experimental_rerun()
            else:
                st.error("Please enter a valid email address.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def user_dir() -> Path:
    u = current_user()
    assert u and u.get("email"), "user must be signed in"
    d = DATA_DIR / _hash_email(u["email"]) 
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_db_path() -> Path:
    return user_dir() / DEFAULT_DB_NAME


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


def load_saved_db_for_user() -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
    path = user_db_path()
    if path.exists():
        try:
            return read_excel_db(path)
        except Exception as e:
            st.warning(f"Saved database couldn't be read: {e}")
    return None


def save_uploaded_file(uploaded, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(uploaded.getbuffer())
    return out_path


def docx_to_html(doc_path: Path) -> Optional[str]:
    try:
        import mammoth  # type: ignore
        with open(doc_path, "rb") as f:
            result = mammoth.convert_to_html(f)
            return result.value
    except Exception:
        try:
            import docx  # type: ignore
            doc = docx.Document(str(doc_path))
            text = "

".join(p.text for p in doc.paragraphs)
            return f"<pre>{text}</pre>"
        except Exception:
            return None


def embed_pdf(file_path: Path, height: int = 900):
    b64 = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>',
        unsafe_allow_html=True,
    )

# ---------- Gate: sign-in first ----------
require_sign_in()

# ---------- Header (after sign-in) ----------
st.markdown("<div class='h1'>🌿 Light LCA Tool</div>", unsafe_allow_html=True)
user = current_user()
st.markdown(
    f"<div class='sub'>Welcome {user.get('name') or user.get('email')} — upload your database, calculate, and open the guide.</div>",
    unsafe_allow_html=True,
)

# ---------- Tabs ----------
TAB_TITLES = ["Calculator", "Database", "User Guide", "Reports", "Settings"]
TabCalc, TabDB, TabGuide, TabRep, TabSet = st.tabs(TAB_TITLES)

# =============================
# Database (per‑user, simple)
# =============================
with TabDB:
    st.markdown("### Database")
    st.caption("Upload one Excel workbook with sheets named 'Processes' and 'Materials'. Your file is saved to your account.")

    uploaded = st.file_uploader("Upload/replace my database (.xlsx)", type=["xlsx"], accept_multiple_files=False)
    preview = st.toggle("Preview tables after upload", value=False)

    if uploaded is not None:
        saved = save_uploaded_file(uploaded, user_db_path())
        try:
            dfp, dfm = read_excel_db(saved)
            st.session_state["df_processes"] = dfp
            st.session_state["df_materials"] = dfm
            st.success("Database saved to your account.")
        except Exception as e:
            st.error(f"Failed to read Excel: {e}")

    # lazy load if not yet in session
    if st.session_state.get("df_processes") is None:
        loaded = load_saved_db_for_user()
        if loaded:
            st.session_state["df_processes"], st.session_state["df_materials"] = loaded

    if preview and st.session_state.get("df_processes") is not None:
        st.subheader("Processes (preview)")
        st.dataframe(st.session_state["df_processes"].head(30), use_container_width=True)
    if preview and st.session_state.get("df_materials") is not None:
        st.subheader("Materials (preview)")
        st.dataframe(st.session_state["df_materials"].head(30), use_container_width=True)

# =============================
# Calculator (clean & focused)
# =============================
with TabCalc:
    st.markdown("### LCA Calculator")

    df_proc = st.session_state.get("df_processes")
    df_mat = st.session_state.get("df_materials")

    if df_proc is None or df_mat is None:
        st.info("No database loaded yet. Go to **Database** and upload your Excel.")
    else:
        # find process name column
        name_col = next((c for c in ["Process", "Name", "Process Name", "process", "name"] if c in df_proc.columns), df_proc.columns[0])
        processes = df_proc[name_col].astype(str).tolist()
        c1, c2 = st.columns([2,1])
        with c1:
            selected_proc = st.selectbox("Process", processes)
        with c2:
            qty = st.number_input("Quantity", min_value=0.0, value=1.0)
        fu = st.text_input("Functional unit", value="unit")

        # impact columns
        impact_cols = [c for c in df_proc.columns if re.search(r"(CO2|GHG|GWP|impact|emission)", str(c), re.I)]
        if not impact_cols:
            st.warning("No impact column detected. Add a column such as 'GWP (kg CO2e/unit)'.")
        else:
            impact_col = st.selectbox("Impact column", impact_cols)
            row = df_proc[df_proc[name_col].astype(str) == str(selected_proc)]
            if row.empty:
                st.error("Selected process not found.")
            else:
                factor = float(row.iloc[0][impact_col]) if pd.notna(row.iloc[0][impact_col]) else 0.0
                total = qty * factor
                st.metric(label=f"Impact factor ({impact_col})", value=f"{factor:,.4f}")
                st.metric(label=f"Total impact for {qty:g} {fu}", value=f"{total:,.4f}")
                st.caption("Tip: Add more impact columns (e.g., energy, water) and select them here.")

# =============================
# User Guide (auto-detect all files)
# =============================
with TabGuide:
    st.markdown("### User Guide")
    st.caption("Place any DOCX/PDF files in ./guides (or upload below). They appear here automatically.")

    # discover all docs dynamically
    def list_guide_files() -> List[Path]:
        docs = list(GUIDE_DIR.glob("*.docx")) + list(GUIDE_DIR.glob("*.pdf"))
        return sorted(docs, key=lambda p: p.name.lower())

    # allow upload
    up = st.file_uploader("Add or replace a guide (DOCX or PDF)", type=["docx", "pdf"], key="guide_upl")
    if up is not None:
        dest = GUIDE_DIR / up.name
        save_uploaded_file(up, dest)
        st.success(f"Saved guide: {up.name}")

    found = list_guide_files()
    if not found:
        st.info("No guide found yet. Upload a DOCX/PDF above or place files into ./guides")
    else:
        choice = st.selectbox("Choose a file", [p.name for p in found])
        chosen = next(p for p in found if p.name == choice)
        if chosen.suffix.lower() == ".docx":
            html = docx_to_html(chosen)
            if html:
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("Couldn't render DOCX inline (install 'mammoth' or 'python-docx').")
                st.download_button("Download DOCX", data=chosen.read_bytes(), file_name=chosen.name)
        else:  # pdf
            try:
                embed_pdf(chosen, height=900)
            except Exception:
                st.download_button("Download PDF", data=chosen.read_bytes(), file_name=chosen.name)

# =============================
# Reports (export current DB)
# =============================
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

# =============================
# Settings (sign out, clear cache)
# =============================
with TabSet:
    st.markdown("### Settings")
    if st.button("Sign out"):
        if "user" in st.session_state:
            del st.session_state["user"]
        for k in ["df_processes", "df_materials"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Signed out.")
        st.experimental_rerun()

    if st.button("Clear in‑memory data"):
        for k in ["df_processes", "df_materials"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Cleared session data.")

# ---------------------------
# End of file
# ---------------------------
