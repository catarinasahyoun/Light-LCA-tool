# Light LCA Tool — refreshed UI + persistent DB + built‑in User Guide
# ---------------------------------------------------------------
# Notes
# - Drop this in your Streamlit project as app.py (replacing the old one).
# - It adds: a polished layout, persistent per‑user database storage,
#   and a "User Guide" tab that renders your DOCX/PDF if present.
# - It avoids auto‑previewing uploaded tables by default (you can turn it on).
# - It reads processes/materials directly from the same uploaded Excel file.
# - If third‑party libraries like `mammoth` or `python-docx` are not installed,
#   the User Guide tab will gracefully fall back to a download link.
#
# Author: ChatGPT (Catou TCHAI)
# ---------------------------------------------------------------

import io
import os
import re
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Tuple, Dict

import pandas as pd
import streamlit as st

# ---------- Page & Theme ----------
st.set_page_config(
    page_title="Light LCA Tool",
    page_icon="🌱",
    layout="wide",
    menu_items={
        "Get Help": "https://docs.streamlit.io/",
        "Report a bug": "mailto:edwinsahyoun24@gmail.com",
        "About": "Light LCA Tool — refreshed UI (Sep 2025)"
    }
)

PRIMARY = "#00A67E"  # teal/green accent
BG_CARD = "#0f172a1a"  # subtle slate overlay

_CUSTOM_CSS = f"""
<style>
/***** Global polish *****/
:root {{
  --brand: {PRIMARY};
}}
.block-container {{
  padding-top: 1.2rem;
  padding-bottom: 3rem;
}}

/***** Section headers *****/
.h-section {{
  font-size: 1.4rem; font-weight: 700; margin: .5rem 0 1rem 0;
}}
.subtitle {{ color: #64748b; margin-top: -6px; }}

/***** Card *****/
.card {{
  background: {BG_CARD};
  border: 1px solid rgba(15,23,42,.08);
  border-radius: 1rem;
  padding: 1rem 1.25rem;
  box-shadow: 0 6px 20px rgba(0,0,0,.05);
}}
.card h3 {{ margin: 0 0 .75rem 0; }}

/***** Buttons *****/
.stButton>button {{
  background: var(--brand) !important;
  color: white !important;
  border-radius: .75rem !important;
  border: 0 !important;
  padding: .55rem 1rem !important;
}}
.stDownloadButton>button {{
  border-radius: .75rem !important;
}}

/***** Tabs *****/
.stTabs [data-baseweb="tab-list"] {{ gap: .25rem; }}
.stTabs [data-baseweb="tab"] {{
  border-radius: .75rem;
  padding-top: .5rem; padding-bottom: .5rem;
}}

/***** Sidebar logo *****/
.sidebar-logo {{ display: flex; align-items: center; gap: .5rem; }}
.sidebar-logo img {{ width: 28px; height: 28px; border-radius: .5rem; }}
.sidebar-logo span {{ font-weight: 700; }}

.small-muted {{ font-size: .85rem; color: #64748b; }}
.kpi {{ font-size: 1.25rem; font-weight: 700; }}
</style>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

# ---------- Utilities ----------
APP_DIR = Path.cwd()
DATA_DIR = APP_DIR / "data"
GUIDE_DIR = APP_DIR / "guides"
DATA_DIR.mkdir(exist_ok=True)
GUIDE_DIR.mkdir(exist_ok=True)

DEFAULT_DB_NAME = "lca_database.xlsx"
PROCESSES_SHEET = "Processes"
MATERIALS_SHEET = "Materials"


def _hash_user(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]


def current_user_folder(email: str) -> Path:
    return DATA_DIR / _hash_user(email)


def save_uploaded_file(uploaded, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(uploaded.getbuffer())
    return out_path


def read_excel_db(path: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read processes & materials from a single Excel workbook.
    Expects sheets named 'Processes' and 'Materials'.
    """
    xl = pd.ExcelFile(path)
    if PROCESSES_SHEET not in xl.sheet_names:
        raise ValueError(f"Missing '{PROCESSES_SHEET}' sheet in {path.name}")
    if MATERIALS_SHEET not in xl.sheet_names:
        raise ValueError(f"Missing '{MATERIALS_SHEET}' sheet in {path.name}")
    df_proc = xl.parse(PROCESSES_SHEET).fillna(0)
    df_mat = xl.parse(MATERIALS_SHEET).fillna(0)
    # normalize headers
    df_proc.columns = [str(c).strip() for c in df_proc.columns]
    df_mat.columns = [str(c).strip() for c in df_mat.columns]
    return df_proc, df_mat


def get_user_db_path() -> Optional[Path]:
    user = st.session_state.get("user", {})
    email = user.get("email")
    if not email:
        return None
    user_dir = current_user_folder(email)
    candidate = user_dir / DEFAULT_DB_NAME
    return candidate if candidate.exists() else None


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
    # fallback to plain text if python-docx is present
    docx = try_import_docx()
    if docx:
        doc = docx.Document(str(doc_path))
        text = "\n\n".join(p.text for p in doc.paragraphs)
        return f"<pre>{text}</pre>"
    return None


def embed_pdf(file_path: Path, height: int = 800):
    b64 = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


# ---------- Sidebar (branding + identity) ----------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-logo">
          <img src="https://raw.githubusercontent.com/enchantedlabs/assets/refs/heads/main/tchai_logo.png" />
          <span>Light LCA Tool</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("""<span class="small-muted">UI refreshed · Sep 2025</span>""", unsafe_allow_html=True)

    # Simple sign-in (email only, no auth provider to keep things lightweight)
    with st.expander("Sign in (for per‑user saved DB)", expanded=False):
        email = st.text_input("Email", key="email_input", placeholder="name@example.com")
        name = st.text_input("Name (optional)", key="name_input")
        if st.button("Sign in"):
            if email and re.match(r"^.+@.+\..+$", email):
                st.session_state["user"] = {"email": email, "name": name}
                st.success("Signed in. Your uploaded database will persist.")
            else:
                st.error("Please enter a valid email.")

    if st.session_state.get("user"):
        u = st.session_state["user"]
        st.caption(f"Signed in as **{u.get('name') or u['email']}**")

# ---------- Header ----------
st.markdown("<div class='h-section'>🌿 Light LCA Tool</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtitle'>Calculate product/process footprints, manage a shared database, and view the built‑in user guide.</div>",
    unsafe_allow_html=True,
)

# ---------- Tabs ----------
TAB_TITLES = ["Dashboard", "LCA Calculator", "Database", "Reports", "User Guide", "Settings"]

Tabs = st.tabs(TAB_TITLES)

# ----- Dashboard -----
with Tabs[0]:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Databases uploaded**")
        st.markdown(f"<div class='kpi'>{len(list(DATA_DIR.rglob(DEFAULT_DB_NAME)))}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Signed‑in user**")
        who = st.session_state.get("user", {}).get("email", "—")
        st.markdown(f"<div class='kpi'>{who}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Guide detected**")
        has_any_guide = any(p.exists() for p in [
            GUIDE_DIR/"LCA-Light Usage Overview (1).docx",
            GUIDE_DIR/"Text_Report of the Easy LCA Tool (1).docx",
            GUIDE_DIR/"LCA Tool Redesign V2 (1).pdf",
            GUIDE_DIR/"LCA Tool.pdf",
        ])
        st.markdown(f"<div class='kpi'>{'Yes' if has_any_guide else 'No'}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Quick tips")
    st.markdown("- Use **Database** to upload one Excel file containing both *Processes* and *Materials* sheets.")
    st.markdown("- Turn on **Preview** only if you need to inspect the raw tables.")
    st.markdown("- Sign in on the left to **persist** your DB per user.")
    st.markdown("</div>", unsafe_allow_html=True)

# ----- LCA Calculator -----
with Tabs[1]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Calculator")

    # Load DB from session or disk
    df_proc = st.session_state.get("df_processes")
    df_mat = st.session_state.get("df_materials")

    if df_proc is None or df_mat is None:
        # try disk for signed-in user
        db_path = get_user_db_path()
        if db_path:
            try:
                df_proc, df_mat = read_excel_db(db_path)
                st.session_state["df_processes"] = df_proc
                st.session_state["df_materials"] = df_mat
            except Exception as e:
                st.warning(f"Could not load your saved DB: {e}")

    if df_proc is None or df_mat is None:
        st.info("No database loaded yet. Upload an Excel workbook first in the **Database** tab.")
    else:
        # Process selection
        name_col = None
        # Prefer a friendly column name if present
        for cand in ["Process", "Name", "Process Name", "process", "name"]:
            if cand in df_proc.columns:
                name_col = cand
                break
        if name_col is None:
            name_col = df_proc.columns[0]

        proc_names = df_proc[name_col].astype(str).tolist()
        selected_proc = st.selectbox("Select a process", proc_names)
        qty = st.number_input("Quantity", min_value=0.0, value=1.0)
        fu = st.text_input("Functional unit (e.g., kg, unit)", value="unit")

        # Emission factor / impact columns detection
        impact_cols = [c for c in df_proc.columns if re.search(r"(CO2|GHG|GWP|impact|emission)", str(c), re.I)]
        if not impact_cols:
            st.warning("No emission/impact columns detected in the Processes sheet. Add a column like 'GWP (kg CO2e/unit)'.")
        else:
            # Use the first detected impact as default
            impact_col = st.selectbox("Impact factor column", impact_cols)
            # Lookup the row
            row = df_proc[df_proc[name_col].astype(str) == str(selected_proc)]
            if row.empty:
                st.error("Selected process not found. Check your Processes sheet.")
            else:
                factor = float(row.iloc[0][impact_col]) if pd.notna(row.iloc[0][impact_col]) else 0.0
                total = qty * factor
                c1, c2 = st.columns(2)
                with c1:
                    st.metric(label=f"Impact factor ({impact_col})", value=f"{factor:,.4f}")
                with c2:
                    st.metric(label=f"Total impact for {qty:g} {fu}", value=f"{total:,.4f}")

                st.caption("Tip: You can add more impact columns (e.g., water, energy) and pick them here.")

    st.markdown("</div>", unsafe_allow_html=True)

# ----- Database -----
with Tabs[2]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Database (single Excel with `Processes` & `Materials` sheets)")

    st.write("Upload or replace your workbook. If you are signed in, it will persist for your account.")
    uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False)

    preview = st.toggle("Preview tables after upload", value=False)

    if uploaded is not None:
        # Save to per-user folder if signed in; else store in session only
        if st.session_state.get("user"):
            user = st.session_state["user"]
            out_path = current_user_folder(user["email"]) / DEFAULT_DB_NAME
            saved_path = save_uploaded_file(uploaded, out_path)
            st.success(f"Saved database for {user.get('name') or user['email']}.")
            try:
                df_proc, df_mat = read_excel_db(saved_path)
                st.session_state["df_processes"] = df_proc
                st.session_state["df_materials"] = df_mat
            except Exception as e:
                st.error(f"Failed to read Excel: {e}")
        else:
            # session-only
            try:
                df_proc, df_mat = read_excel_db(Path(uploaded.name))  # this uses in-memory name; fallback below
            except Exception:
                # read from bytes buffer
                uploaded.seek(0)
                with pd.ExcelFile(uploaded) as xl:
                    if PROCESSES_SHEET not in xl.sheet_names or MATERIALS_SHEET not in xl.sheet_names:
                        st.error("Excel must contain 'Processes' and 'Materials' sheets.")
                    else:
                        df_proc = xl.parse(PROCESSES_SHEET).fillna(0)
                        df_mat = xl.parse(MATERIALS_SHEET).fillna(0)
            st.session_state["df_processes"] = df_proc
            st.session_state["df_materials"] = df_mat
            st.success("Database loaded for this session. Sign in to persist across sessions.")

    # Offer explicit load from disk if signed in
    if st.session_state.get("user") and st.button("Load my saved database"):
        db_path = get_user_db_path()
        if db_path:
            try:
                df_proc, df_mat = read_excel_db(db_path)
                st.session_state["df_processes"] = df_proc
                st.session_state["df_materials"] = df_mat
                st.success("Database loaded from disk.")
            except Exception as e:
                st.error(f"Failed to read saved Excel: {e}")
        else:
            st.info("No saved database found yet.")

    # Show preview if requested
    if st.session_state.get("df_processes") is not None and preview:
        st.subheader("Processes (preview)")
        st.dataframe(st.session_state["df_processes"].head(30), use_container_width=True)
    if st.session_state.get("df_materials") is not None and preview:
        st.subheader("Materials (preview)")
        st.dataframe(st.session_state["df_materials"].head(30), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ----- Reports -----
with Tabs[3]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Reports")
    if st.session_state.get("df_processes") is None:
        st.info("Run a few calculations and/or load a database to enable exports.")
    else:
        # For now, just allow exporting both sheets
        with io.BytesIO() as output:
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                st.session_state["df_processes"].to_excel(writer, sheet_name="Processes", index=False)
                if st.session_state.get("df_materials") is not None:
                    st.session_state["df_materials"].to_excel(writer, sheet_name="Materials", index=False)
            data = output.getvalue()
        st.download_button("Download current DB (xlsx)", data=data, file_name="lca_current_db.xlsx")

    st.markdown("</div>", unsafe_allow_html=True)

# ----- User Guide -----
with Tabs[4]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### User Guide")

    st.write("This tab renders your provided documentation if present in the `guides/` folder next to the app.")

    # Detect available files from your uploads (place them into guides/ on the server)
    candidates = [
        GUIDE_DIR/"LCA-Light Usage Overview (1).docx",
        GUIDE_DIR/"Text_Report of the Easy LCA Tool (1).docx",
        GUIDE_DIR/"LCA Tool Redesign V2 (1).pdf",
        GUIDE_DIR/"LCA Tool.pdf",
    ]

    found = [p for p in candidates if p.exists()]

    # Allow runtime upload of a guide too (optional)
    up_guide = st.file_uploader("Add/replace a guide (DOCX or PDF)", type=["docx", "pdf"], key="guide_upl")
    if up_guide is not None:
        dest = GUIDE_DIR / up_guide.name
        save_uploaded_file(up_guide, dest)
        st.success(f"Saved guide: {up_guide.name}")
        found.insert(0, dest)

    if not found:
        st.info("No guide files found yet. Upload a DOCX/PDF above or place them into the `guides/` folder.")
    else:
        # Choose which doc to render
        choice = st.selectbox("Choose a document to view", [p.name for p in found])
        chosen = next(p for p in found if p.name == choice)

        if chosen.suffix.lower() == ".docx":
            html = docx_to_html(chosen)
            if html:
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("Couldn't render the DOCX inline (missing `mammoth`/`python-docx`).")
                st.download_button("Download DOCX", data=chosen.read_bytes(), file_name=chosen.name)
        elif chosen.suffix.lower() == ".pdf":
            try:
                embed_pdf(chosen, height=900)
            except Exception:
                st.download_button("Download PDF", data=chosen.read_bytes(), file_name=chosen.name)
        else:
            st.download_button("Download file", data=chosen.read_bytes(), file_name=chosen.name)

    st.markdown("</div>", unsafe_allow_html=True)

# ----- Settings -----
with Tabs[5]:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### Settings & Maintenance")

    # Allow clearing the session cache
    if st.button("Clear in‑memory data"):
        for k in ["df_processes", "df_materials"]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Cleared session data.")

    # Delete saved DB for this user
    if st.session_state.get("user"):
        user_dir = current_user_folder(st.session_state["user"]["email"])
        if (user_dir / DEFAULT_DB_NAME).exists():
            if st.button("Delete my saved database"):
                try:
                    (user_dir / DEFAULT_DB_NAME).unlink(missing_ok=True)
                    st.success("Deleted your saved database.")
                except Exception as e:
                    st.error(f"Couldn't delete: {e}")
    else:
        st.caption("Sign in (left) to manage your persisted database.")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# End of file
# ---------------------------
