"""
Enhanced LCA Tool (Streamlit)
- Modern visuals (cards, tabs, charts)
- Simple user sign-in (demo)
- Data entry via form or CSV upload
- Downloadable HTML report + CSV export
- Modular code for easy feature additions later

How to run:
  pip install streamlit pandas numpy plotly
  streamlit run app.py

Notes:
- Authentication here is a lightweight demo for local use. Replace with a proper auth provider (e.g., Auth0, Firebase, streamlit-authenticator) before production.
- The visual design includes a clean theme plus a "Dark Neon" toggle.
"""

from __future__ import annotations
import io
import json
import base64
from dataclasses import dataclass
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------
# Theming / global page config
# ----------------------------
st.set_page_config(page_title="LCA Tool", page_icon="♻️", layout="wide")

# Inject optional custom CSS themes
CUSTOM_CSS = """
/* Clean baseline */
:root { --brand: #0ea5e9; --brand-2: #22c55e; }
.block-container { padding-top: 1.5rem; }
/* Card style */
.stMetric { background: #ffffff; border-radius: 16px; padding: 1rem; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
/* Section headers */
section h2, .stTabs [data-baseweb="tab-list"] { font-weight: 700; }
/* Dark Neon option */
body.dark .block-container { background: #0b1220; }
body.dark .stMetric { background: #0e1628; color: #f3f4f6; box-shadow: 0 2px 16px rgba(0,255,255,0.08); }
body.dark .stButton>button, body.dark .stDownloadButton>button { background: linear-gradient(90deg,#00f5d4,#00bbf9); color: #0b1220; border: none; }
body.dark .stSelectbox, body.dark .stTextInput, body.dark .stNumberInput { color: #e5e7eb; }
"""

# A light/dark toggle using a query param for persistence across reruns
if "theme" not in st.session_state:
    st.session_state.theme = st.experimental_get_query_params().get("theme", ["clean"]) [0]

st.markdown(f"""
<style>
{CUSTOM_CSS}
</style>
<script>
const params = new URLSearchParams(window.location.search);
const theme = params.get('theme') || '{st.session_state.theme}';
document.body.classList.toggle('dark', theme === 'dark');
</script>
""", unsafe_allow_html=True)

# ----------------------------
# Minimal demo authentication
# ----------------------------
@dataclass
class User:
    username: str
    full_name: str

DEMO_USERS = {
    "edwin": {"password": "test123", "full_name": "Edwin Sahyoun"},
    "demo": {"password": "demo", "full_name": "Demo User"},
}


def login_panel() -> Optional[User]:
    with st.sidebar:
        st.header("🔐 Sign in")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        colA, colB = st.columns([1,1])
        login_clicked = colA.button("Sign in", use_container_width=True)
        theme_choice = colB.selectbox("Theme", ["clean", "dark"], index=(1 if st.session_state.theme=="dark" else 0))
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.experimental_set_query_params(theme=theme_choice)
            st.rerun()

        if login_clicked:
            rec = DEMO_USERS.get(username)
            if rec and rec["password"] == password:
                st.session_state.user = User(username=username, full_name=rec["full_name"])  # type: ignore
                st.success(f"Welcome {rec['full_name']}!")
                st.rerun()
            else:
                st.error("Invalid credentials. Try demo/demo.")

    return st.session_state.get("user")


# ----------------------------
# Data model & computations
# ----------------------------
@dataclass
class Activity:
    name: str
    quantity: float
    unit: str
    emission_factor: float  # kg CO2e per unit

    @property
    def emissions(self) -> float:
        return self.quantity * self.emission_factor


def default_catalog() -> pd.DataFrame:
    data = [
        {"name": "Electricity (grid)", "unit": "kWh", "emission_factor": 0.42},
        {"name": "Diesel", "unit": "L", "emission_factor": 2.68},
        {"name": "Steel", "unit": "kg", "emission_factor": 1.9},
        {"name": "Concrete", "unit": "kg", "emission_factor": 0.12},
        {"name": "Transport (truck)", "unit": "ton-km", "emission_factor": 0.12},
    ]
    return pd.DataFrame(data)


def activities_from_df(df: pd.DataFrame) -> List[Activity]:
    rows = []
    for _, r in df.iterrows():
        try:
            rows.append(Activity(name=str(r["name"]).strip(),
                                 quantity=float(r["quantity"]),
                                 unit=str(r["unit"]).strip(),
                                 emission_factor=float(r["emission_factor"])) )
        except Exception:
            continue
    return rows


def compute_summary(acts: List[Activity]) -> pd.DataFrame:
    if not acts:
        return pd.DataFrame(columns=["Activity", "Quantity", "Unit", "EF (kg CO2e/unit)", "Emissions (kg CO2e)"])
    recs = [{"Activity": a.name,
             "Quantity": a.quantity,
             "Unit": a.unit,
             "EF (kg CO2e/unit)": a.emission_factor,
             "Emissions (kg CO2e)": a.emissions} for a in acts]
    df = pd.DataFrame(recs)
    df.loc["Total"] = ["—", "—", "—", "—", df["Emissions (kg CO2e)"].sum()]
    return df


def breakdown_by_category(acts: List[Activity]) -> pd.DataFrame:
    # naive category mapping from names
    def cat(name: str) -> str:
        n = name.lower()
        if any(k in n for k in ["electric", "grid"]):
            return "Electricity"
        if any(k in n for k in ["diesel", "fuel"]):
            return "Fuel"
        if any(k in n for k in ["steel", "concrete", "material"]):
            return "Materials"
        if any(k in n for k in ["transport", "truck", "ship"]):
            return "Transport"
        return "Other"
    return pd.DataFrame(
        {"Category": [cat(a.name) for a in acts],
         "Emissions": [a.emissions for a in acts]}
    ).groupby("Category", as_index=False).sum().sort_values("Emissions", ascending=False)


# ----------------------------
# Visualization helpers
# ----------------------------

def plot_category_bar(breakdown: pd.DataFrame):
    fig = go.Figure(data=[go.Bar(x=breakdown["Category"], y=breakdown["Emissions"], text=breakdown["Emissions"].round(1), textposition='auto')])
    fig.update_layout(height=380, margin=dict(l=10,r=10,t=30,b=10), title="Emissions by Category (kg CO2e)")
    st.plotly_chart(fig, use_container_width=True)


def plot_pareto(breakdown: pd.DataFrame):
    if breakdown.empty:
        return
    df = breakdown.copy().sort_values("Emissions", ascending=False)
    df["cum_share"] = df["Emissions"].cumsum() / df["Emissions"].sum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Category"], y=df["Emissions"], name="Emissions"))
    fig.add_trace(go.Scatter(x=df["Category"], y=(df["cum_share"]*100).round(1), yaxis="y2", name="Cumulative %"))
    fig.update_layout(
        height=380,
        margin=dict(l=10,r=10,t=30,b=10),
        title="Pareto of Categories",
        yaxis=dict(title="kg CO2e"),
        yaxis2=dict(title="%", overlaying='y', side='right', range=[0,100])
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_sankey(acts: List[Activity]):
    if not acts:
        return
    # Build a simple source->category->total Sankey
    cats = {}
    def get_cat(a: Activity):
        n = a.name.lower()
        if any(k in n for k in ["electric", "grid"]): return "Electricity"
        if any(k in n for k in ["diesel", "fuel"]): return "Fuel"
        if any(k in n for k in ["steel", "concrete", "material"]): return "Materials"
        if any(k in n for k in ["transport", "truck", "ship"]): return "Transport"
        return "Other"
    categories = sorted(set(get_cat(a) for a in acts))
    sources = [a.name for a in acts]
    labels = sources + categories + ["Total"]
    idx = {lab:i for i,lab in enumerate(labels)}

    # links: source -> category, category -> Total
    src, tgt, val = [], [], []
    cat_totals = {c:0.0 for c in categories}
    for a in acts:
        c = get_cat(a)
        src.append(idx[a.name]); tgt.append(idx[c]); val.append(a.emissions)
        cat_totals[c]+=a.emissions
    for c, v in cat_totals.items():
        src.append(idx[c]); tgt.append(idx["Total"]); val.append(v)

    fig = go.Figure(data=[go.Sankey(
        node=dict(label=labels, pad=15, thickness=18),
        link=dict(source=src, target=tgt, value=val)
    )])
    fig.update_layout(height=500, margin=dict(l=10,r=10,t=30,b=10), title="Flow of Emissions")
    st.plotly_chart(fig, use_container_width=True)


# ----------------------------
# Report generation (HTML + CSV)
# ----------------------------

def generate_html_report(project_name: str, df_summary: pd.DataFrame, df_breakdown: pd.DataFrame, notes: str) -> bytes:
    total = 0.0
    if not df_summary.empty and "Emissions (kg CO2e)" in df_summary.columns and "Total" in df_summary.index:
        total = float(df_summary.loc["Total", "Emissions (kg CO2e)"])
    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='utf-8'/>
<title>LCA Report - {project_name}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; }}
h1 {{ color: #0ea5e9; }}
.table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
.table th, .table td {{ border: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
.badge {{ display: inline-block; background: #e0f2fe; color: #0369a1; padding: 6px 10px; border-radius: 999px; font-weight: 700; }}
.note {{ background: #f8fafc; padding: 12px; border-radius: 12px; }}
</style>
</head>
<body>
  <h1>Life Cycle Assessment Report</h1>
  <p><strong>Project:</strong> {project_name}</p>
  <p><span class='badge'>Total Emissions: {total:.2f} kg CO2e</span></p>
  <h2>Activity Summary</h2>
  {df_summary.to_html(classes='table', border=0)}
  <h2>Breakdown by Category</h2>
  {df_breakdown.to_html(classes='table', border=0, index=False)}
  <h2>Notes</h2>
  <div class='note'>{notes if notes else '—'}</div>
</body>
</html>
"""
    return html.encode("utf-8")


# ----------------------------
# App UI
# ----------------------------

def app():
    user = login_panel()
    st.title("♻️ LCA Tool")
    if not user:
        st.info("Use demo/demo to sign in. Once signed in, you can enter data, visualize, and export a report.")
        st.stop()

    # Sidebar: Project info + upload
    with st.sidebar:
        st.subheader("Project")
        project_name = st.text_input("Project name", value="Sample Project")
        st.subheader("Data Catalog")
        catalog_df = default_catalog()
        with st.expander("View default emission factors"):
            st.dataframe(catalog_df, use_container_width=True)
        uploaded = st.file_uploader("Upload activities CSV (name,quantity,unit,emission_factor)", type=["csv"])    

    st.write("")
    tab_input, tab_results, tab_report, tab_settings = st.tabs(["Data Entry", "Results & Visuals", "Report", "Settings"])

    # --------------------
    # Data Entry tab
    # --------------------
    with tab_input:
        st.subheader("Enter Activities")
        acts: List[Activity] = []
        col1, col2 = st.columns([2,1])
        with col1:
            with st.form("manual_input"):
                st.caption("Quick add from catalog")
                selected = st.selectbox("Activity", options=["(custom)"] + catalog_df["name"].tolist())
                if selected != "(custom)":
                    row = catalog_df[catalog_df["name"]==selected].iloc[0]
                    name = selected
                    unit = row["unit"]
                    ef = float(row["emission_factor"])
                else:
                    name = st.text_input("Name", value="Electricity (grid)")
                    unit = st.text_input("Unit", value="kWh")
                    ef = st.number_input("Emission factor (kg CO2e / unit)", min_value=0.0, step=0.01, value=0.42)
                qty = st.number_input("Quantity", min_value=0.0, step=0.1, value=100.0)
                add_btn = st.form_submit_button("Add activity")
                if add_btn:
                    stash = st.session_state.setdefault("activities", [])
                    stash.append({"name": name, "quantity": qty, "unit": unit, "emission_factor": ef})
                    st.success(f"Added {name}")
        with col2:
            st.caption("Manage")
            if st.button("Clear activities", type="secondary"):
                st.session_state["activities"] = []
                st.warning("Cleared.")
            st.write("\n")
            if uploaded is not None:
                try:
                    df_up = pd.read_csv(uploaded)
                    st.session_state["activities"] = df_up.to_dict(orient="records")
                    st.success("Loaded from CSV")
                except Exception as e:
                    st.error(f"Failed to read CSV: {e}")

        st.write("\n")
        st.subheader("Current Activities")
        data_recs = st.session_state.get("activities", [])
        df_current = pd.DataFrame(data_recs)
        if not df_current.empty:
            st.dataframe(df_current, use_container_width=True, hide_index=True)
        else:
            st.info("No activities yet. Add one above or upload a CSV.")

    # --------------------
    # Results tab
    # --------------------
    with tab_results:
        st.subheader("Results & Visuals")
        acts = activities_from_df(pd.DataFrame(st.session_state.get("activities", [])))
        df_summary = compute_summary(acts)
        df_breakdown = breakdown_by_category(acts) if acts else pd.DataFrame(columns=["Category","Emissions"])

        c1, c2, c3 = st.columns(3)
        total = float(df_summary.loc["Total", "Emissions (kg CO2e)"]) if "Total" in df_summary.index else 0.0
        c1.metric("Total emissions", f"{total:,.2f}", help="kg CO2e")
        c2.metric("# of activities", f"{len(acts)}")
        c3.metric("Categories", f"{df_breakdown['Category'].nunique() if not df_breakdown.empty else 0}")

        left, right = st.columns([1.1, 1])
        with left:
            plot_category_bar(df_breakdown)
            plot_pareto(df_breakdown)
        with right:
            plot_sankey(acts)

        st.markdown("### Detailed Summary")
        st.dataframe(df_summary, use_container_width=True)

    # --------------------
    # Report tab
    # --------------------
    with tab_report:
        st.subheader("Generate Report")
        notes = st.text_area("Executive notes (optional)")
        acts = activities_from_df(pd.DataFrame(st.session_state.get("activities", [])))
        df_summary = compute_summary(acts)
        df_breakdown = breakdown_by_category(acts) if acts else pd.DataFrame(columns=["Category","Emissions"])

        # HTML report
        html_bytes = generate_html_report(project_name, df_summary, df_breakdown, notes)
        st.download_button("⬇️ Download HTML report", data=html_bytes, file_name=f"LCA_Report_{project_name.replace(' ','_')}.html", mime="text/html")

        # CSV export
        if not df_summary.empty:
            csv = df_summary.to_csv(index=True).encode("utf-8")
            st.download_button("⬇️ Download CSV (summary)", data=csv, file_name=f"LCA_Summary_{project_name.replace(' ','_')}.csv", mime="text/csv")
        else:
            st.caption("(Add activities to enable exports)")

    # --------------------
    # Settings tab (placeholders for future features)
    # --------------------
    with tab_settings:
        st.subheader("Settings & Admin")
        st.toggle("Enable advanced charts (beta)")
        st.toggle("Show debug info")
        st.caption("Future ideas: versioned projects, multi-user teams, emission factor libraries, API integrations, real sign-in.")


if __name__ == "__main__":
    app()
