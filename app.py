# TCHAI — Easy LCA Indicator

import streamlit as st
import pandas as pd
import plotly.express as px
import json, os, hashlib, secrets
from pathlib import Path
from datetime import datetime

# ------------------------ Paths & Folders ---------------------
APP_DIR = Path.cwd()
ASSETS = APP_DIR / "assets"
DATA_DIR = APP_DIR / "user_data"

# Ensure ASSETS is a directory even if a file named 'assets' exists
if ASSETS.exists() and not ASSETS.is_dir():
    ASSETS = APP_DIR / "assets_dir"
ASSETS.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = ASSETS / "users.json"
DEFAULT_LOGO = ASSETS / "tchai_logo.png"

# ------------------------ Utilities ---------------------------
BRAND_PURPLE = ["#6B2FB3"]

@st.cache_data(show_spinner=False)
def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def read_json(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def write_json(path: Path, data: dict):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)

# ------------------------ Auth --------------------------------

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def _load_users() -> dict:
    return read_json(USERS_FILE, {})

def _save_users(users: dict):
    write_json(USERS_FILE, users)

def create_account(username: str, password: str):
    users = _load_users()
    if username in users:
        return False, "Username already exists."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    salt = secrets.token_hex(16)
    users[username] = {
        "salt": salt,
        "pwd": _hash_password(password, salt),
        "db_path": None,
        "logo_path": None,
        "created_at": _now_str(),
        "last_login": None,
    }
    _save_users(users)
    return True, "Account created. Please sign in."

def verify_login(username: str, password: str):
    users = _load_users()
    u = users.get(username)
    if not u:
        return False, "User not found."
    ok = _hash_password(password, u["salt"]) == u["pwd"]
    if ok:
        u["last_login"] = _now_str()
        users[username] = u
        _save_users(users)
        return True, "Signed in."
    return False, "Incorrect password."

# --------------------- Database handling ----------------------

@st.cache_data(show_spinner=False)
def _read_excel(path: str) -> dict:
    """Return a dict of DataFrames keyed by sheet name."""
    xls = pd.ExcelFile(path)
    frames = {}
    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet)
            if df is not None and not df.empty:
                # Normalize column names
                df.columns = [str(c).strip() for c in df.columns]
                frames[sheet.strip()] = df
        except Exception:
            continue
    return frames

@st.cache_data(show_spinner=False)
def _detect_processes(frames: dict):
    """Pick the Processes sheet if present; otherwise pick first with numeric cols."""
    if not frames:
        return None
    # Prefer sheet called 'Processes' (case-insensitive)
    for k in frames:
        if k.lower() == "processes":
            return frames[k]
    # Otherwise choose the first sheet that has at least 1 numeric column
    for k, df in frames.items():
        if any(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
            return df
    # Fallback: first sheet
    first = next(iter(frames.values()))
    return first

@st.cache_data(show_spinner=False)
def _detect_materials(frames: dict):
    for k in frames:
        if k.lower() == "materials":
            return frames[k]
    return None

# --------------------- UI Helpers -----------------------------

def header():
    with st.container():
        cols = st.columns([1, 6, 1])
        with cols[0]:
            # Prioritize user logo if set, else default
            logo_path = DEFAULT_LOGO
            if st.session_state.get("user_logo") and Path(st.session_state["user_logo"]).exists():
                logo_path = Path(st.session_state["user_logo"]) 
            if logo_path.exists():
                st.image(str(logo_path), use_column_width=True)
        with cols[1]:
            st.markdown("""
                <div style='text-align:center; margin-top:6px;'>
                    <h1 style='margin: 0; font-weight:800;'>TCHAI — Easy LCA Indicator</h1>
                    <p style='margin: 0; color:#333;'>Black & White UI · Purple Charts</p>
                </div>
            """, unsafe_allow_html=True)
        with cols[2]:
            if st.session_state.get("username"):
                st.caption(f"Signed in as **{st.session_state['username']}**")

def sidebar():
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Database", "Visualize", "Report", "Settings"], index=0)
    st.session_state["page"] = page

    st.sidebar.markdown("---")
    if st.session_state.get("username"):
        if st.sidebar.button("Sign out"):
            for k in ["username", "db_frames", "db_path", "user_logo"]:
                st.session_state.pop(k, None)
            st.experimental_rerun()
    else:
        st.sidebar.info("Create an account or sign in to start.")

def auth_box():
    st.subheader("Account")
    tabs = st.tabs(["Sign in", "Create account"])
    with tabs[0]:
        user = st.text_input("Username", key="signin_user")
        pwd = st.text_input("Password", type="password", key="signin_pwd")
        if st.button("Sign in"):
            ok, msg = verify_login(user.strip(), pwd)
            if ok:
                st.success(msg)
                st.session_state["username"] = user.strip()
                # Load persisted paths
                users = _load_users()
                u = users.get(st.session_state["username"], {})
                # Persist DB
                if u.get("db_path") and Path(u["db_path"]).exists():
                    st.session_state["db_path"] = u["db_path"]
                    frames = _read_excel(u["db_path"])
                    st.session_state["db_frames"] = frames if frames else None
                # Persist logo
                if u.get("logo_path") and Path(u["logo_path"]).exists():
                    st.session_state["user_logo"] = u["logo_path"]
                st.experimental_rerun()
            else:
                st.error(msg)
    with tabs[1]:
        user = st.text_input("New username", key="signup_user")
        pwd = st.text_input("New password", type="password", key="signup_pwd")
        if st.button("Create account"):
            ok, msg = create_account(user.strip(), pwd)
            (st.success if ok else st.error)(msg)

# ---------------------- Pages ---------------------------------

def page_home():
    st.write("Welcome to the Easy LCA Indicator. Use the sidebar to navigate.")
    if not st.session_state.get("username"):
        with st.expander("Sign in to get started"):
            auth_box()

def _save_user_db(uploaded):
    users = _load_users()
    user = st.session_state.get("username")
    if not user:
        st.error("Please sign in first.")
        return False
    user_dir = DATA_DIR / hashlib.sha256(user.encode()).hexdigest()[:16]
    user_dir.mkdir(parents=True, exist_ok=True)
    db_path = user_dir / "database.xlsx"
    with open(db_path, "wb") as f:
        f.write(uploaded.getbuffer())
    users[user]["db_path"] = str(db_path)
    _save_users(users)
    st.session_state["db_path"] = str(db_path)
    st.session_state["db_frames"] = _read_excel(str(db_path))
    return True

def page_database():
    st.subheader("Your LCA Database")

    if not st.session_state.get("username"):
        st.info("Please sign in to upload and persist your database.")
        auth_box()
        return

    st.write("Upload a single Excel file containing your **Processes** and (optionally) **Materials** sheets. The app will use the processes from this same file.")

    up = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"], accept_multiple_files=False)
    if up is not None:
        if _save_user_db(up):
            st.success("Database saved to your account. (No preview is shown by design.)")

    # Show current status without preview
    db_path = st.session_state.get("db_path")
    if db_path and Path(db_path).exists():
        frames = st.session_state.get("db_frames") or _read_excel(db_path)
        st.session_state["db_frames"] = frames
        proc = _detect_processes(frames)
        mats = _detect_materials(frames)
        bullets = []
        bullets.append(f"File: **{Path(db_path).name}**")
        bullets.append(f"Sheets loaded: **{', '.join(frames.keys())}**")
        bullets.append(f"Processes sheet used: **{[k for k in frames if frames[k] is proc][0]}**")
        if mats is not None:
            bullets.append("Materials sheet detected: **yes**")
        else:
            bullets.append("Materials sheet detected: **no**")
        st.markdown("\n".join(["- "+b for b in bullets]))
    else:
        st.info("No database on file yet.")

def page_visualize():
    st.subheader("Visualize Impacts")
    if not st.session_state.get("db_frames"):
        st.warning("Upload your database first (see Database page).")
        return

    frames = st.session_state["db_frames"]
    proc = _detect_processes(frames)
    if proc is None or proc.empty:
        st.error("No processes table found or it's empty.")
        return

    # Let user pick label and value columns dynamically
    cols = list(proc.columns)
    text_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(proc[c])]
    num_cols  = [c for c in cols if pd.api.types.is_numeric_dtype(proc[c])]

    if not num_cols:
        st.error("No numeric columns found to chart.")
        return

    label_col = st.selectbox("Label column (x)", options=text_cols or cols, index=0)
    value_col = st.selectbox("Value column (y)", options=num_cols, index=0)

    df_plot = proc[[label_col, value_col]].dropna()
    if df_plot.empty:
        st.info("Nothing to chart with current selection.")
        return

    fig = px.bar(df_plot, x=label_col, y=value_col, title=f"{value_col} by {label_col}", color_discrete_sequence=BRAND_PURPLE)
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        title_x=0.5,
        font=dict(color="#111"),
        xaxis=dict(showgrid=True, gridcolor="#eee"),
        yaxis=dict(showgrid=True, gridcolor="#eee"),
    )
    st.plotly_chart(fig, use_container_width=True)

def _build_report_html(frames: dict) -> str:
    proc = _detect_processes(frames)
    mats = _detect_materials(frames)
    n_proc = 0 if proc is None else len(proc)
    n_mats = 0 if mats is None else len(mats)
    return f"""
<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>TCHAI LCA Report</title>
<style>
body {{ font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial; color:#111; }}
h1, h2 {{ text-align:center; }}
.badge {{ display:inline-block; padding:4px 10px; border:1px solid #000; border-radius:999px; }}
hr {{ border:0; border-top:1px solid #000; }}
</style></head>
<body>
    <h1>TCHAI — Easy LCA Indicator</h1>
    <p style='text-align:center;'>Generated: {_now_str()}</p>
    <div style='text-align:center;margin:12px 0;'>
        <span class='badge'>Black & White UI</span>
        <span class='badge'>Purple Charts</span>
    </div>
    <hr/>
    <h2>Database Summary</h2>
    <ul>
        <li>Sheets: {', '.join(frames.keys())}</li>
        <li>Processes rows: {n_proc}</li>
        <li>Materials rows: {n_mats}</li>
    </ul>
</body></html>
"""

def page_report():
    st.subheader("Report & Exports")
    if not st.session_state.get("db_frames"):
        st.warning("Upload your database first (see Database page).")
        return

    frames = st.session_state["db_frames"]

    # HTML report
    html = _build_report_html(frames)
    st.download_button("Download HTML Report", data=html.encode("utf-8"), file_name="tchai_lca_report.html", mime="text/html")

    # CSV exports (zipped into one if multiple?) — keep simple: offer each sheet
    for name, df in frames.items():
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(f"Download '{name}' as CSV", data=csv, file_name=f"{name}.csv", mime="text/csv")

def page_settings():
    st.subheader("Settings")
    if not st.session_state.get("username"):
        st.info("Sign in to customize your logo.")
        auth_box()
        return

    st.write("Upload a custom logo to override the default TCHAI logo.")
    up = st.file_uploader("Upload PNG/JPG", type=["png", "jpg", "jpeg"], accept_multiple_files=False)
    if up is not None:
        users = _load_users()
        user = st.session_state["username"]
        user_dir = DATA_DIR / hashlib.sha256(user.encode()).hexdigest()[:16]
        user_dir.mkdir(parents=True, exist_ok=True)
        logo_path = user_dir / "logo.png"
        with open(logo_path, "wb") as f:
            f.write(up.getbuffer())
        users[user]["logo_path"] = str(logo_path)
        _save_users(users)
        st.session_state["user_logo"] = str(logo_path)
        st.success("Logo saved.")

    # Info about where files live
    st.caption(f"Assets folder: {ASSETS}")
    st.caption(f"User data folder: {DATA_DIR}")

# ---------------------- App Layout ----------------------------

st.set_page_config(page_title="TCHAI — Easy LCA", layout="wide")

# Header + Nav
header()
sidebar()

# Routing
page = st.session_state.get("page", "Home")
if page == "Home":
    page_home()
elif page == "Database":
    page_database()
elif page == "Visualize":
    page_visualize()
elif page == "Report":
    page_report()
elif page == "Settings":
    page_settings()

# Footer
st.write("\n")
st.markdown("<hr style='border:1px solid #000' />", unsafe_allow_html=True)
st.caption("© TCHAI — Easy LCA Indicator. Built with Streamlit.")
