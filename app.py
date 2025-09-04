import streamlit as st
import pandas as pd
import plotly.express as px
import json, os, re, io, hashlib, secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# =============================================================
# TCHAI — Easy LCA Indicator (Clean, Robust Rewrite)
# -------------------------------------------------------------
# Key features implemented from your feedback & docs:
# - Full-screen sign-in gate (create account / sign in)
# - Per-user persistence: uploaded database is saved to disk and reloaded automatically on next login
# - No table preview after upload (just a clean success message with counts)
# - Robust Excel parsing (auto-detects likely sheets/columns for processes & impacts)
# - Black & white UI; charts in purple (#6A0DAD)
# - Real TCHAI logo (assets/tchai_logo.png if available, else fallback text)
# - Simple, ergonomic navigation: Sidebar holds Inputs only; main area is a single “Workspace” with tabs
# - Versions: every run can be saved with a name; you can restore/compare versions later
# - Report downloads (HTML + CSV)
# - Defensive programming around files/paths; friendly errors
# =============================================================

# -------------------------
# Paths & constants
# -------------------------
BASE_DIR = Path(os.getcwd())
ASSETS = BASE_DIR / "assets"
ASSETS.mkdir(exist_ok=True)
USERS_FILE = BASE_DIR / "users.json"
USER_DATA = BASE_DIR / "user_data"
USER_DATA.mkdir(exist_ok=True)
LOGO_FILE = ASSETS / "tchai_logo.png"
FALLBACK_LOGO = "/mnt/data/tchai_logo.png"  # present in this environment
PURPLE = "#6A0DAD"

# -------------------------
# Small utilities
# -------------------------

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_users() -> Dict[str, Any]:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_users(users: Dict[str, Any]) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _hash_password(pw: str, salt: str) -> str:
    return _sha256_hex(pw + ":" + salt)


def get_user_root(username: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", username).lower()
    root = USER_DATA / safe
    root.mkdir(exist_ok=True)
    (root / "versions").mkdir(exist_ok=True)
    return root


def store_user_file(username: str, uploaded_file) -> Path:
    root = get_user_root(username)
    db_path = root / "database.xlsx"
    # Save original bytes so we can fully reload
    bytes_data = uploaded_file.read()
    db_path.write_bytes(bytes_data)
    # Also mark as current in a tiny state file
    (root / "state.json").write_text(json.dumps({"current_db": str(db_path.name), "updated": datetime.utcnow().isoformat()}), encoding="utf-8")
    return db_path


def load_user_db_path(username: str) -> Optional[Path]:
    root = get_user_root(username)
    state_file = root / "state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            name = state.get("current_db")
            if name:
                p = root / name
                if p.exists():
                    return p
        except Exception:
            return None
    # Fallback to default filename if present
    p = root / "database.xlsx"
    return p if p.exists() else None


# -------------------------
# Excel parsing helpers
# -------------------------
EXPECTED_PROCESS_COLUMNS = {"process", "process_name", "name", "activity", "activity_name"}
EXPECTED_IMPACT_COLUMNS = {
    # common impact metric names; we will detect anything numeric otherwise
    "gwp", "co2", "co2e", "co2eq", "carbon", "energy", "water", "land", "acidification",
    "eutrophication", "odp", "pof", "pm", "resource", "toxicity"
}


def read_excel_flex(path_or_file) -> Dict[str, pd.DataFrame]:
    """Read all sheets into a dict; gracefully handle odd files."""
    try:
        xl = pd.ExcelFile(path_or_file)
        sheets = {}
        for s in xl.sheet_names:
            try:
                df = xl.parse(s)
                if not isinstance(df, pd.DataFrame):
                    continue
                # Normalize col names
                df.columns = [str(c).strip() for c in df.columns]
                sheets[s] = df
            except Exception:
                continue
        return sheets
    except Exception as e:
        raise RuntimeError(f"Could not read Excel: {e}")


def detect_process_table(sheets: Dict[str, pd.DataFrame]) -> Tuple[str, pd.DataFrame]:
    """Return (sheet_name, df) that likely contains processes."""
    # 1) prefer a sheet literally named like processes
    for key in sheets:
        if re.search(r"process", key, re.I):
            return key, sheets[key]
    # 2) search for a sheet with a column that matches EXPECTED_PROCESS_COLUMNS
    for key, df in sheets.items():
        cols = set([c.lower() for c in df.columns])
        if cols & EXPECTED_PROCESS_COLUMNS:
            return key, df
    # 3) fallback to first non-empty sheet
    for key, df in sheets.items():
        if len(df.columns) > 0 and len(df) > 0:
            return key, df
    raise RuntimeError("No usable sheet was found in the Excel file.")


def normalize_process_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Standardize name column
    name_col = None
    for c in df.columns:
        if c.lower() in EXPECTED_PROCESS_COLUMNS:
            name_col = c
            break
    if name_col is None:
        # create a synthetic name if none found
        df.insert(0, "Process", [f"Process {i+1}" for i in range(len(df))])
        name_col = "Process"
    else:
        if name_col != "Process":
            df.rename(columns={name_col: "Process"}, inplace=True)
    # Identify numeric impact columns
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    # Heuristic: if some numeric columns match known impact names, use those first
    impact_cols = []
    for c in numeric_cols:
        low = c.lower().strip()
        token = re.sub(r"[^a-z]", "", low)
        if token in EXPECTED_IMPACT_COLUMNS:
            impact_cols.append(c)
    # If none matched, just use all numeric columns except obvious qty/id
    if not impact_cols:
        impact_cols = [c for c in numeric_cols if not re.search(r"id|index|qty|quantity|amount|count", c, re.I)]
    # If still empty, keep any numeric
    if not impact_cols and numeric_cols:
        impact_cols = numeric_cols
    # Ensure uniqueness and order
    impact_cols = list(dict.fromkeys(impact_cols))
    # Keep only Process + impacts + any quantity if present
    keep = ["Process"] + impact_cols
    # Add quantity if available
    qty_col = None
    for c in df.columns:
        if re.search(r"^(qty|quantity|amount|mass|kg|t|tonnage)$", c, re.I):
            qty_col = c; break
    if qty_col and qty_col not in keep:
        keep.append(qty_col)
    # Reduce & drop fully empty rows
    slim = df[[c for c in keep if c in df.columns]].copy()
    slim = slim.dropna(how="all")
    # Fill NA for numeric with 0, names forward-fill if needed
    for c in slim.columns:
        if c == "Process":
            slim[c] = slim[c].astype(str).str.strip().replace({"nan": ""}).replace({"": None}).ffill()
        elif pd.api.types.is_numeric_dtype(slim[c]):
            slim[c] = slim[c].fillna(0)
    return slim


def compute_impacts(df: pd.DataFrame, weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """Compute a simple weighted total across impact columns per process.
    - If weights is None, each numeric impact column has weight 1.0
    - Quantity (if present) will multiply impacts (intensity * qty)
    """
    df = df.copy()
    impacts = [c for c in df.columns if c not in ("Process",) and pd.api.types.is_numeric_dtype(df[c])]
    qty_col = None
    for c in ("quantity", "qty", "amount", "mass", "kg", "t", "tonnage"):
        for col in df.columns:
            if col.lower() == c:
                qty_col = col
                break
        if qty_col:
            break

    # default equal weights
    weights = weights or {c: 1.0 for c in impacts}

    # total per process
    total_vals = []
    for _, row in df.iterrows():
        total = 0.0
        for c in impacts:
            w = float(weights.get(c, 1.0))
            val = float(row.get(c, 0) or 0)
            total += w * val
        if qty_col:
            q = float(row.get(qty_col, 1) or 1)
            total *= q
        total_vals.append(total)
    out = df[["Process"]].copy()
    out["TotalImpact"] = total_vals
    # normalize additional metrics for display
    for c in impacts:
        out[c] = df[c]
    if qty_col:
        out[qty_col] = df[qty_col]
    return out


# -------------------------
# UI helpers
# -------------------------

def show_logo_and_header():
    cols = st.columns([1, 8, 1])
    with cols[0]:
        logo_path = None
        if LOGO_FILE.exists():
            logo_path = str(LOGO_FILE)
        elif Path(FALLBACK_LOGO).exists():
            logo_path = FALLBACK_LOGO
        if logo_path:
            st.image(logo_path, caption=None, use_column_width=True)
        else:
            st.markdown("### TCHAI")
    with cols[1]:
        st.markdown("""
        <div style='text-align:center; font-size: 32px; font-weight:700;'>
            EASY LCA INDICATOR
        </div>
        """, unsafe_allow_html=True)


def sign_in_gate() -> Optional[str]:
    users = _load_users()
    st.markdown("<h2 style='text-align:center;'>Sign in to TCHAI Easy LCA</h2>", unsafe_allow_html=True)
    mode = st.radio("", ["Sign in", "Create account"], horizontal=True)
    username = st.text_input("Username", key="auth_user")
    password = st.text_input("Password", type="password", key="auth_pw")

    if mode == "Create account":
        if st.button("Create account", use_container_width=True):
            if not username or not password:
                st.error("Please enter both a username and a password.")
            elif username in users:
                st.error("This username already exists. Please choose another.")
            else:
                salt = secrets.token_hex(8)
                users[username] = {
                    "salt": salt,
                    "hash": _hash_password(password, salt),
                    "created": datetime.utcnow().isoformat()
                }
                _save_users(users)
                st.success("Account created. You can sign in now.")
    else:
        if st.button("Sign in", type="primary", use_container_width=True):
            if username not in users:
                st.error("Unknown username.")
            else:
                salt = users[username]["salt"]
                if users[username]["hash"] == _hash_password(password, salt):
                    st.session_state["auth_user"] = username
                    st.experimental_rerun()
                else:
                    st.error("Incorrect password.")

    return None


# -------------------------
# Main App
# -------------------------

st.set_page_config(page_title="TCHAI — Easy LCA", layout="wide")

# Minimal black/white with purple accents via inline CSS
st.markdown(
    f"""
    <style>
    :root {{ --purple: {PURPLE}; }}
    .stApp {{ background: #ffffff; color: #111; }}
    .stTabs [data-baseweb="tab"] p {{ font-weight: 600; }}
    .stButton>button {{ border-radius: 12px; border:1px solid #111; }}
    .stRadio>div>label {{ font-weight:600; }}
    .metric-card {{ border:1px solid #ddd; border-radius:16px; padding:16px; }}
    .center {{ text-align:center; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Auth flow
user = st.session_state.get("auth_user")
if not user:
    sign_in_gate()
    st.stop()

# Logged in UI
with st.sidebar:
    st.markdown("### Inputs")
    st.caption("Upload or reuse your saved database. Your files are stored per account.")
    use_saved = False
    saved_path = load_user_db_path(user)

    if saved_path and saved_path.exists():
        use_saved = st.toggle(f"Use saved database ({saved_path.name})", value=True)
    up = st.file_uploader("Upload Excel database (.xlsx)", type=["xlsx"], accept_multiple_files=False)

    if up is not None and not use_saved:
        try:
            db_path = store_user_file(user, up)
            st.success(f"Database saved as {db_path.name}. It will persist for your account.")
            st.session_state["db_path"] = str(db_path)
        except Exception as e:
            st.error(f"Failed to save the uploaded file: {e}")
    elif use_saved and saved_path:
        st.session_state["db_path"] = str(saved_path)

    # Optional: allow custom weights for detected impact columns later (shown in Workspace after load)

# Header with logo + title
show_logo_and_header()

st.divider()

# Workspace tabs
res_tab, cmp_tab, sum_tab, rep_tab, ver_tab = st.tabs([
    "Results", "Comparison", "Final Summary", "Report", "Versions"
])

# -------------------------
# Load & parse database
# -------------------------

def load_and_prepare_current() -> Tuple[pd.DataFrame, Dict[str, float]]:
    dbp = st.session_state.get("db_path")
    if not dbp:
        raise RuntimeError("No database selected or uploaded yet.")
    sheets = read_excel_flex(dbp)
    sheet_name, proc_df = detect_process_table(sheets)
    slim = normalize_process_table(proc_df)

    # Build default weights (1.0 per impact column except Process)
    impacts = [c for c in slim.columns if c != "Process" and pd.api.types.is_numeric_dtype(slim[c])]
    weights = {c: 1.0 for c in impacts}
    return slim, weights


# -------------------------
# RESULTS TAB
# -------------------------
with res_tab:
    st.subheader("Results")
    if "db_path" not in st.session_state:
        st.info("Upload (or reuse) a database from the sidebar to view results.")
    else:
        try:
            df_slim, default_weights = load_and_prepare_current()
            # Let user tune weights (advanced)
            with st.expander("Impact Weights (optional)"):
                cols = st.columns(min(4, max(1, len(default_weights))))
                new_weights = {}
                i = 0
                for k, v in default_weights.items():
                    with cols[i % len(cols)]:
                        new_weights[k] = st.number_input(f"{k}", value=float(v), step=0.1, key=f"w_{k}")
                    i += 1
            if not new_weights:
                new_weights = default_weights

            result_df = compute_impacts(df_slim, new_weights)

            # KPI ribbon
            total_system = float(result_df["TotalImpact"].sum())
            n_proc = int(result_df["Process"].nunique())
            st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
            k1, k2 = st.columns(2)
            k1.metric("Total Impact (weighted)", f"{total_system:,.2f}")
            k2.metric("# Processes detected", f"{n_proc}")
            st.markdown("</div>", unsafe_allow_html=True)

            # Top contributors chart
            topN = st.slider("Show top N processes", 3, 25, 10)
            top_df = result_df.sort_values("TotalImpact", ascending=False).head(topN)
            fig = px.bar(
                top_df,
                x="Process",
                y="TotalImpact",
                title="Top Contributors",
                labels={"TotalImpact": "Weighted Impact"},
                color_discrete_sequence=[PURPLE],
            )
            fig.update_layout(title_x=0.5)
            st.plotly_chart(fig, use_container_width=True)

            # Store current results for other tabs
            st.session_state["current_results"] = result_df
            st.session_state["current_weights"] = new_weights
            st.session_state["current_dataset_info"] = {
                "rows": int(len(df_slim)),
                "impacts": list(new_weights.keys()),
            }
            st.success("Database parsed successfully. Processes and impacts detected.")
        except Exception as e:
            st.error(f"Failed to parse or compute results: {e}")

# -------------------------
# COMPARISON TAB
# -------------------------
with cmp_tab:
    st.subheader("Comparison")
    root = get_user_root(user)
    versions_dir = root / "versions"
    versions = sorted([p for p in versions_dir.glob("*.csv")], key=lambda p: p.stat().st_mtime, reverse=True)

    if not versions:
        st.info("No saved versions yet. Save one from the Versions tab after running Results.")
    else:
        left, right = st.columns(2)
        with left:
            v1 = st.selectbox("Baseline version", versions, format_func=lambda p: p.stem)
        with right:
            v2 = st.selectbox("Comparison version", versions, index=min(1, len(versions)-1), format_func=lambda p: p.stem)
        if v1 and v2 and v1 != v2:
            df1 = pd.read_csv(v1)
            df2 = pd.read_csv(v2)
            merged = df1[["Process", "TotalImpact"]].merge(df2[["Process", "TotalImpact"]], on="Process", how="outer", suffixes=("_A", "_B"))
            merged.fillna(0, inplace=True)
            merged["Delta"] = merged["TotalImpact_B"] - merged["TotalImpact_A"]
            st.dataframe(merged.sort_values("Delta", ascending=False), use_container_width=True)
            fig = px.bar(merged.sort_values("Delta", ascending=False).head(20), x="Process", y="Delta", title="Impact Delta (B - A)", color_discrete_sequence=[PURPLE])
            fig.update_layout(title_x=0.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different saved versions to compare.")

# -------------------------
# FINAL SUMMARY TAB
# -------------------------
with sum_tab:
    st.subheader("Final Summary")
    cur = st.session_state.get("current_results")
    info = st.session_state.get("current_dataset_info")
    if cur is None:
        st.info("Run Results first.")
    else:
        total = float(cur["TotalImpact"].sum())
        top = cur.sort_values("TotalImpact", ascending=False).head(5)[["Process", "TotalImpact"]]
        c1, c2 = st.columns([2,1])
        with c1:
            st.markdown("**Key takeaways**")
            st.markdown(f"- Total weighted system impact: **{total:,.2f}**")
            st.markdown(f"- Processes detected: **{info['rows']}**")
            st.markdown("- Impact metrics considered: " + ", ".join([f"`{m}`" for m in info["impacts"]]))
            st.markdown("**Top 5 contributors**")
            st.table(top)
        with c2:
            fig2 = px.pie(cur, names="Process", values="TotalImpact", title="Share of Impact", color_discrete_sequence=[PURPLE])
            fig2.update_layout(title_x=0.5)
            st.plotly_chart(fig2, use_container_width=True)

# -------------------------
# REPORT TAB
# -------------------------
with rep_tab:
    st.subheader("Report & Exports")
    cur = st.session_state.get("current_results")
    if cur is None:
        st.info("Run Results first.")
    else:
        # CSV download
        csv = cur.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV of Results", csv, file_name="easy_lca_results.csv")

        # Simple HTML report (self-contained)
        def build_html_report(df: pd.DataFrame) -> str:
            total = float(df["TotalImpact"].sum())
            top = df.sort_values("TotalImpact", ascending=False).head(10)
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            html = f"""
            <html><head><meta charset='utf-8'>
            <style>
            body {{ font-family: Arial, sans-serif; color:#111; }}
            h1, h2 {{ text-align: center; }}
            table {{ border-collapse: collapse; width:100%; }}
            th, td {{ border:1px solid #ccc; padding:8px; text-align:left; }}
            .pill {{ display:inline-block; padding:4px 10px; border-radius:999px; border:1px solid #111; }}
            </style></head>
            <body>
              <h1>TCHAI — Easy LCA Report</h1>
              <p class="pill">Generated: {now}</p>
              <h2>Total Weighted Impact: {total:,.2f}</h2>
              <h3>Top 10 Contributors</h3>
              {top.to_html(index=False)}
            </body></nhtml>
            """
            return html
        html = build_html_report(cur)
        st.download_button("Download HTML Report", data=html, file_name="easy_lca_report.html")
        st.success("Exports are ready.")

# -------------------------
# VERSIONS TAB
# -------------------------
with ver_tab:
    st.subheader("Versions")
    cur = st.session_state.get("current_results")
    if cur is None:
        st.info("Run Results first to save a version.")
    else:
        default_name = datetime.now().strftime("run-%Y%m%d-%H%M")
        vname = st.text_input("Version name", value=default_name)
        if st.button("Save current as version"):
            try:
                path = get_user_root(user) / "versions" / f"{vname}.csv"
                cur.to_csv(path, index=False)
                st.success(f"Saved version: {path.name}")
            except Exception as e:
                st.error(f"Failed to save version: {e}")

        # List versions
        root = get_user_root(user)
        versions = sorted([(p, p.stat().st_mtime) for p in (root / "versions").glob("*.csv")], key=lambda x: x[1], reverse=True)
        if versions:
            st.markdown("**Saved versions**")
            for p, ts in versions:
                st.write(f"- {p.stem} ({datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')})")
        else:
            st.caption("No versions saved yet.")

# -------------------------
# End
# -------------------------
