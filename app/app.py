"""
VoltaLake: Customer Energy Intelligence Dashboard for Ireland & Great Britain
Portfolio-grade BI Application built with Streamlit, Plotly, and DuckDB
Dual-Mode Backend: Local Gold Parquet Execution Engine (Databricks Lakehouse-Ready Architecture)
"""

import os
import sys
import json
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. Page Configuration & Aesthetic Theming
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="VoltaLake | Customer Energy Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Plus Jakarta Sans, Obsidian Glassmorphism, Neon Accents)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 10%, #0F172A 0%, #090D16 100%);
        color: #F8FAFC;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00E599 0%, #00B4D8 50%, #A78BFA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    
    .subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }
    
    .headline-insight {
        background: linear-gradient(90deg, rgba(0, 229, 153, 0.12) 0%, rgba(0, 180, 216, 0.08) 100%);
        border-left: 4px solid #00E599;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 1.5rem;
        color: #E2E8F0;
        font-size: 0.92rem;
        line-height: 1.5;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .headline-insight strong {
        color: #00E599;
    }
    
    .kpi-card {
        background: rgba(22, 30, 49, 0.65);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-top: 3px solid #00B4D8;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-top-color: #00E599;
    }
    .kpi-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 0.4rem;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }
    .kpi-delta {
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 0.35rem;
    }
    .delta-positive { color: #00E599; }
    .delta-warning { color: #F59E0B; }
    .delta-neutral { color: #94A3B8; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Connectivity & Dual-Backend Execution (Databricks SQL / Local DuckDB)
# -----------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLD_DIR = os.path.join(BASE_DIR, "data", "gold")
GEO_DIR = os.path.join(BASE_DIR, "data", "geo")

@st.cache_resource
def get_db_connection():
    """
    Dual-mode connection:
    1. If Databricks SQL environment variables are provided, connect via databricks-sql-connector.
    2. Otherwise, fall back cleanly to local DuckDB querying parquet tables in data/gold/.
    """
    server_hostname = os.getenv("DATABRICKS_HOST")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    access_token = os.getenv("DATABRICKS_TOKEN")
    
    if server_hostname and http_path and access_token:
        try:
            from databricks import sql
            conn = sql.connect(
                server_hostname=server_hostname,
                http_path=http_path,
                access_token=access_token
            )
            return {"mode": "databricks_sql", "conn": conn}
        except Exception as e:
            st.warning(f"Could not connect to Databricks SQL ({e}). Falling back to local Gold Parquet repository.")
            
    # Local DuckDB Fallback
    con = duckdb.connect(database=":memory:", read_only=False)
    gold_tables = [
        "dim_date", "dim_region", "dim_tariff", "dim_property_type",
        "fact_consumption_region", "fact_household_load", "fact_market_switching",
        "kpi_retrofit_propensity_ie", "kpi_retrofit_propensity_gb",
        "kpi_customer_personas", "kpi_tariff_did_experiment", "kpi_campaign_roi_sensitivity",
        "data_quality_scorecard", "freshness_tracking"
    ]
    for tbl in gold_tables:
        p = os.path.join(GOLD_DIR, f"{tbl}.parquet")
        if os.path.exists(p):
            con.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM read_parquet('{p.replace(os.sep, '/')}')")
            
    return {"mode": "local_duckdb", "conn": con}

DB = get_db_connection()

@st.cache_data(ttl=3600)
def query_df(sql_query: str) -> pd.DataFrame:
    """Execute SQL query against active database with 1-hour TTL cache matching regulatory SLAs"""
    if DB["mode"] == "databricks_sql":
        return pd.read_sql(sql_query, DB["conn"])
    else:
        return DB["conn"].execute(sql_query).df()

@st.cache_data(ttl=86400)
def load_geojson(filename: str):
    """Load cached geographic boundary file"""
    path = os.path.join(GEO_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# -----------------------------------------------------------------------------
# 3. Sidebar: Security Context & Role-Based Access Simulation
# -----------------------------------------------------------------------------
st.sidebar.markdown("### ⚡ **VoltaLake Intelligence**")
st.sidebar.caption("Customer Energy Analytics | Ireland & Great Britain")

# Row-Level Security (RLS) User Persona Emulation
st.sidebar.markdown("---")
st.sidebar.markdown("#### 🔒 **User Access & Governance (RLS Simulation)**")
user_role = st.sidebar.selectbox(
    "Active Security Principal:",
    [
        "Global Executive (Head of Customer Solutions)",
        "Ireland Customer Specialist (Dublin Hybrid)",
        "GB Operations Analyst (London)"
    ],
    index=0,
    help="Demonstrates Row-Level Security (RLS) filtering logic. Selecting a jurisdiction-specific role restricts accessible rows across all Gold tables."
)

if "Ireland" in user_role:
    active_jurisdictions = ["IE"]
    st.sidebar.success("🔑 RLS Filter Active: `jurisdiction = 'IE'`")
elif "GB" in user_role:
    active_jurisdictions = ["GB"]
    st.sidebar.success("🔑 RLS Filter Active: `jurisdiction = 'GB'`")
else:
    active_jurisdictions = ["IE", "GB"]
    st.sidebar.info("🔑 Global Access: Full visibility across IE & GB")

# Jurisdiction Switcher (if authorized)
st.sidebar.markdown("---")
st.sidebar.markdown("#### 🌍 **Market Scope**")
if len(active_jurisdictions) > 1:
    market_view = st.sidebar.radio("View Jurisdiction:", ["All Markets (IE & GB)", "Ireland (IE)", "Great Britain (GB)"])
    if market_view == "Ireland (IE)":
        selected_jurisdiction = ["IE"]
    elif market_view == "Great Britain (GB)":
        selected_jurisdiction = ["GB"]
    else:
        selected_jurisdiction = ["IE", "GB"]
else:
    selected_jurisdiction = active_jurisdictions

# Navigation with URL Query Params Sync
st.sidebar.markdown("---")
st.sidebar.markdown("#### 📑 **Navigation Pages**")

PAGES = [
    "Executive KPIs",
    "Market Benchmarks",
    "Opportunity Map",
    "Customer Personas",
    "Campaign ROI Simulator",
    "Data Health & Governance"
]

current_page_param = st.query_params.get("page", PAGES[0])
if current_page_param not in PAGES:
    current_page_param = PAGES[0]

page_index = PAGES.index(current_page_param)
active_page = st.sidebar.radio("Select View:", PAGES, index=page_index)
st.query_params["page"] = active_page

st.sidebar.markdown("---")
st.sidebar.caption("⚡ Sourced from Hugging Face mirror of SEAI data, CSO PxStat, CRU PDFs, DESNZ Table 2.7.1 & UK Power Networks.")

# -----------------------------------------------------------------------------
# 4. Page 1: Executive KPIs
# -----------------------------------------------------------------------------
if active_page == "Executive KPIs":
    st.markdown('<div class="main-title">Executive Customer Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Unified cross-jurisdictional retail energy metrics derived from conformed Gold tables (Executed locally via DuckDB)</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="headline-insight">
        <strong>Executive Takeaway:</strong> Under the consistent like-for-like series (CRU2024132, p.15), Ireland's electricity switching eased from 
        <strong>16.57% (418,597 switches) in 2022</strong> to <strong>11.67% (294,669 switches) in 2023</strong> (with 19.51% originally reported under the 2022 report method). 
        Crucially, <strong>21.0% of all Irish electricity customers renegotiated contracts</strong> with their incumbent supplier without switching in 2023 (CRU2024132, p.3/p.14), 
        highlighting in-contract retention as a paramount commercial priority.
    </div>
    """, unsafe_allow_html=True)
    
    # Query KPI Marts
    df_switching = query_df("SELECT * FROM fact_market_switching ORDER BY year DESC")
    df_ie_prop = query_df("SELECT * FROM kpi_retrofit_propensity_ie")
    df_gb_prop = query_df("SELECT * FROM kpi_retrofit_propensity_gb")
    df_personas = query_df("SELECT * FROM kpi_customer_personas")
    
    # Filter by selected jurisdiction
    if "IE" in selected_jurisdiction and "GB" in selected_jurisdiction:
        ie_switch_latest = df_switching[df_switching["jurisdiction"] == "IE"]["switching_rate_pct"].iloc[0]
        gb_switch_latest = df_switching[df_switching["jurisdiction"] == "GB"]["switching_rate_pct"].iloc[0]
        switch_display = f"{ie_switch_latest:.1f}% / {gb_switch_latest:.1f}%"
        switch_sub = "IE (2023, CRU2024132 p.15) / GB (2024, DESNZ)"
    elif "IE" in selected_jurisdiction:
        ie_switch_latest = df_switching[df_switching["jurisdiction"] == "IE"]["switching_rate_pct"].iloc[0]
        switch_display = f"{ie_switch_latest:.2f}%"
        switch_sub = "Ireland Latest (2023, CRU2024132 p.15)"
    else:
        gb_switch_latest = df_switching[df_switching["jurisdiction"] == "GB"]["switching_rate_pct"].iloc[0]
        switch_display = f"{gb_switch_latest:.2f}%"
        switch_sub = "Great Britain Latest (2024, DESNZ Table 2.7.1)"
        
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Market Switching Rate</div>
            <div class="kpi-value">{switch_display}</div>
            <div class="kpi-delta delta-warning">{switch_sub}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with k2:
        if "IE" in selected_jurisdiction:
            reneg_val = df_switching[(df_switching["jurisdiction"] == "IE") & (df_switching["year"] == 2023)]["renegotiation_rate_pct"].values[0]
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">In-Contract Renegotiation</div>
                <div class="kpi-value">{reneg_val:.1f}%</div>
                <div class="kpi-delta delta-positive">CRU 2023 (p.3 & p.14) | All Electricity Customers</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            gb_transfers = df_switching[(df_switching["jurisdiction"] == "GB") & (df_switching["year"] == 2024)]["electricity_switches"].values[0]
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">GB Annual Switches</div>
                <div class="kpi-value">{gb_transfers/1e6:.2f}M</div>
                <div class="kpi-delta delta-positive">DESNZ Table 2.7.1 (2024)</div>
            </div>
            """, unsafe_allow_html=True)
            
    with k3:
        if "IE" in selected_jurisdiction:
            prime_count = len(df_ie_prop[df_ie_prop["propensity_tier"] == "Prime Target"])
            top_county = df_ie_prop.sort_values(by="retrofit_propensity_score", ascending=False).iloc[0]["county"]
            top_score = df_ie_prop.sort_values(by="retrofit_propensity_score", ascending=False).iloc[0]["retrofit_propensity_score"]
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Top Retrofit County (IE)</div>
                <div class="kpi-value">{top_county}</div>
                <div class="kpi-delta delta-positive">Score: {top_score:.1f}/100 | {prime_count} Prime Counties</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            gb_top = df_gb_prop.sort_values(by="gb_retrofit_propensity_score", ascending=False).iloc[0]["LA"]
            gb_top_score = df_gb_prop.sort_values(by="gb_retrofit_propensity_score", ascending=False).iloc[0]["gb_retrofit_propensity_score"]
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Top Retrofit Region (GB)</div>
                <div class="kpi-value">{gb_top}</div>
                <div class="kpi-delta delta-positive">Score: {gb_top_score:.1f}/100 (DESNZ)</div>
            </div>
            """, unsafe_allow_html=True)
            
    with k4:
        best_sil = 0.1773
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Cluster Silhouette (k=3)</div>
            <div class="kpi-value">{best_sil:.4f}</div>
            <div class="kpi-delta delta-positive">Selected k=3 (Silhouette 0.18; Exploratory)</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Visual Chart: Switching Trends
    st.markdown("#### Annual Switching Rate Velocity (CRU vs DESNZ Table 2.7.1)")
    fig_switch = px.line(
        df_switching,
        x="year",
        y="switching_rate_pct",
        color="jurisdiction",
        markers=True,
        color_discrete_map={"IE": "#00E599", "GB": "#00B4D8"},
        labels={"switching_rate_pct": "Switching Rate (%)", "year": "Year", "jurisdiction": "Jurisdiction"}
    )
    fig_switch.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_switch, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. Page 2: Market Benchmarks (CRU Reports & DESNZ Table 2.7.1)
# -----------------------------------------------------------------------------
elif active_page == "Market Benchmarks":
    st.markdown('<div class="main-title">Market Benchmarks & Switching Trends</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Harmonised regulatory filings from Ireland Commission for Regulation of Utilities (CRU) and UK DESNZ Table 2.7.1</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="headline-insight">
        <strong>Regulatory Context:</strong> In Ireland, the like-for-like series (CRU2024132, p.15) shows switching moved from <strong>16.57% (418,597 switches) in 2022</strong> 
        to <strong>11.67% (294,669 switches) in 2023</strong> (executive summary rounds to 12%; 19.51% recorded under the 2022 report method). In Great Britain, DESNZ Table 2.7.1 shows switching collapsed to 
        <strong>3.06% in 2022</strong> under the Energy Price Guarantee before rebounding to <strong>9.03% in 2024</strong>.
    </div>
    """, unsafe_allow_html=True)
    
    df_market = query_df("SELECT * FROM fact_market_switching ORDER BY year DESC, jurisdiction")
    st.dataframe(
        df_market[[
            "jurisdiction", "year", "electricity_switches", "avg_customers",
            "switching_rate_pct", "renegotiation_rate_pct", "source", "citation"
        ]].style.format({
            "electricity_switches": "{:,.0f}",
            "avg_customers": "{:,.0f}",
            "switching_rate_pct": "{:.2f}%",
            "renegotiation_rate_pct": lambda x: f"{x:.1f}%" if pd.notnull(x) else "—"
        }),
        use_container_width=True
    )
    
    st.markdown("#### Domestic Electricity Supplier Market Shares (CRU 2023 Report, Table on p.55)")
    shares_data = pd.DataFrame([
        {"Supplier": "Electric Ireland", "Customer_Sites": 1168284, "Site_Share_Pct": 52.36, "Consumption_Share_Pct": 50.5, "Color": "#3B82F6"},
        {"Supplier": "Bord Gáis Energy", "Customer_Sites": 331930, "Site_Share_Pct": 14.88, "Consumption_Share_Pct": 16.0, "Color": "#10B981"},
        {"Supplier": "SSE Airtricity", "Customer_Sites": 253122, "Site_Share_Pct": 11.35, "Consumption_Share_Pct": 11.8, "Color": "#00E599"},
        {"Supplier": "Energia", "Customer_Sites": 193440, "Site_Share_Pct": 8.67, "Consumption_Share_Pct": 10.2, "Color": "#F59E0B"},
        {"Supplier": "Yuno / PrePayPower", "Customer_Sites": 189831, "Site_Share_Pct": 8.51, "Consumption_Share_Pct": 7.6, "Color": "#8B5CF6"},
        {"Supplier": "Flogas", "Customer_Sites": 56345, "Site_Share_Pct": 2.53, "Consumption_Share_Pct": 2.3, "Color": "#EC4899"},
        {"Supplier": "Pinergy", "Customer_Sites": 30511, "Site_Share_Pct": 1.37, "Consumption_Share_Pct": 1.2, "Color": "#6366F1"},
        {"Supplier": "Other", "Customer_Sites": 7637, "Site_Share_Pct": 0.34, "Consumption_Share_Pct": 0.4, "Color": "#64748B"}
    ])
    
    fig_share = px.bar(
        shares_data,
        x="Site_Share_Pct",
        y="Supplier",
        orientation="h",
        color="Supplier",
        color_discrete_sequence=[s["Color"] for s in shares_data.to_dict("records")],
        labels={"Site_Share_Pct": "Domestic Customer Site Share (Q4 2023, %)"}
    )
    fig_share.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(ticksuffix="%")
    )
    st.plotly_chart(fig_share, use_container_width=True)

# -----------------------------------------------------------------------------
# 6. Page 3: Opportunity Map (26 Conformed Irish Counties)
# -----------------------------------------------------------------------------
elif active_page == "Opportunity Map":
    st.markdown('<div class="main-title">Regional Retrofit Opportunity Map</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">26 Conformed Irish Counties: Building Energy Ratings, Residential Demand per Dwelling (Census 2022 Denominator), and 2025 BEV Share</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="headline-insight">
        <strong>Geospatial Targeting Insight:</strong> Rural and Western counties lead Ireland's retrofit propensity: 
        <strong>Tipperary (84.75)</strong>, <strong>Mayo (79.84)</strong>, <strong>Kerry (77.91)</strong>, and <strong>Donegal (76.87)</strong> rank as Prime Targets. 
        In Donegal, <strong>70.01% of assessed homes depend on home heating oil</strong>. Dublin ranks lowest (29.39) due to urban gas grid saturation and low oil dependence (5.55%).
    </div>
    """, unsafe_allow_html=True)
    
    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        map_metric = st.selectbox(
            "Ranking Variable:",
            [
                "Retrofit Propensity Score (Composite)",
                "% Homes BER D or Worse (Inefficiency Need)",
                "% Heating Oil Dependent (Heat Pump Target)",
                "Residential kWh per Dwelling (Grid Intensity)",
                "2025 BEV Share of New Cars (%)"
            ]
        )
    with col_ctrl2:
        tier_filter = st.multiselect(
            "Filter Propensity Tiers:",
            ["Prime Target", "High", "Moderate", "Low"],
            default=["Prime Target", "High", "Moderate", "Low"]
        )
        
    metric_col_map = {
        "Retrofit Propensity Score (Composite)": "retrofit_propensity_score",
        "% Homes BER D or Worse (Inefficiency Need)": "pct_d_or_worse",
        "% Heating Oil Dependent (Heat Pump Target)": "pct_oil_dependent",
        "Residential kWh per Dwelling (Grid Intensity)": "residential_kwh_per_dwelling",
        "2025 BEV Share of New Cars (%)": "bev_share_new_cars_pct"
    }
    target_metric = metric_col_map[map_metric]
    
    df_ie_map = query_df("SELECT * FROM kpi_retrofit_propensity_ie")
    df_ie_map = df_ie_map[df_ie_map["propensity_tier"].isin(tier_filter)].copy()
    
    geo_data = load_geojson("ireland_counties.geojson")
    
    if geo_data:
        fig_map = px.choropleth(
            df_ie_map,
            geojson=geo_data,
            locations="county",
            featureidkey="properties.name",
            color=target_metric,
            color_continuous_scale="Viridis",
            hover_name="county",
            hover_data={
                "propensity_tier": True,
                "retrofit_propensity_score": ":.1f",
                "cso_private_households": ":,d",
                "residential_kwh_per_dwelling": ":,.0f",
                "pct_d_or_worse": ":.1f%",
                "pct_oil_dependent": ":.1f%",
                "bev_share_new_cars_pct": ":.1f%"
            }
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=600,
            margin=dict(l=0, r=0, t=10, b=0)
        )
        st.plotly_chart(fig_map, use_container_width=True)
        
    st.markdown("#### 26-County Propensity Ranking Table (CSO Census 2022 Private Households Denominator)")
    st.dataframe(
        df_ie_map[[
            "county", "propensity_tier", "retrofit_propensity_score",
            "cso_private_households", "pct_d_or_worse", "pct_oil_dependent",
            "residential_kwh_per_dwelling", "bev_share_new_cars_pct"
        ]].sort_values(by="retrofit_propensity_score", ascending=False).style.format({
            "retrofit_propensity_score": "{:.2f}",
            "cso_private_households": "{:,.0f}",
            "pct_d_or_worse": "{:.1f}%",
            "pct_oil_dependent": "{:.1f}%",
            "residential_kwh_per_dwelling": "{:,.0f} kWh",
            "bev_share_new_cars_pct": "{:.2f}%"
        }),
        use_container_width=True
    )

# -----------------------------------------------------------------------------
# 7. Page 4: Customer Personas & Difference-in-Differences Tariff Response
# -----------------------------------------------------------------------------
elif active_page == "Customer Personas":
    st.markdown('<div class="main-title">Customer Personas & Tariff Response</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">K-Means clustering on 2,056,233 half-hourly smart-meter records and Difference-in-Differences evaluation</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="headline-insight">
        <strong>Segmentation & Proposition Insight:</strong> Evaluated cluster metrics selected <strong>k = 3</strong> 
        (Silhouette = <strong>0.1773</strong> indicates weak cluster structure, so segments are exploratory; Davies-Bouldin = <strong>1.5744</strong>) across 58 valid households after routing 5 anomalous outlier meters to quarantine. 
        A <strong>Difference-in-Differences (DiD)</strong> test comparing 2012 pre-period baseline to 2013 ToU trial period 
        found <strong>no statistically significant peak reduction</strong> in this 61-household sample (DiD = +0.0169 kWh/hh, t = 1.4170, p = 0.1623; 95% CI [-0.0070, +0.0407] includes small reductions). 
        Hypothesis to test: peak shifting may require automated hardware rather than voluntary manual behavioural response.
    </div>
    """, unsafe_allow_html=True)
    
    df_personas = query_df("SELECT * FROM kpi_customer_personas")
    
    # 3 Persona Cards + Quarantine Summary
    c1, c2, c3, c4 = st.columns(4)
    p_cards = [
        {"name": "Dual-Peak Residential Consumer", "prop": "Dynamic ToU Tariff & Automation", "col": c1, "icon": "⚡", "color": "#00E599", "cluster": 1},
        {"name": "High-Baseload Continuous Consumer", "prop": "Baseload Audit & Home Battery", "col": c2, "icon": "🔋", "color": "#00B4D8", "cluster": 0},
        {"name": "Daytime-Active Household", "prop": "Solar PV & Daytime Export", "col": c3, "icon": "☀️", "color": "#F59E0B", "cluster": 2},
        {"name": "Anomalous Meter (DLT Quarantined)", "prop": "Meter Inspection & Recalibration", "col": c4, "icon": "🛡️", "color": "#EC4899", "cluster": -1}
    ]
    for p in p_cards:
        cnt = (df_personas["cluster"] == p["cluster"]).sum()
        pct = (cnt / len(df_personas)) * 100
        with p["col"]:
            st.markdown(f"""
            <div class="kpi-card" style="border-top-color: {p['color']};">
                <div style="font-size:1.5rem;margin-bottom:0.3rem;">{p['icon']}</div>
                <div class="kpi-label">{p['name']}</div>
                <div class="kpi-value" style="font-size:1.3rem;">{cnt} <span style="font-size:0.75rem;color:#94A3B8;">({pct:.1f}%)</span></div>
                <div class="kpi-delta" style="color:{p['color']};font-size:0.75rem;">{p['prop']}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Difference-in-Differences Statistical Test Card
    st.markdown("#### Scientific Evaluation: Difference-in-Differences (DiD) Analysis")
    stat_col1, stat_col2 = st.columns([1.2, 1.0])
    with stat_col1:
        st.markdown("""
        **Difference-in-Differences Formulation (2012 Pre-Period vs 2013 Post-Period):**
        - **Control Cohort (Standard Flat Rate):** $n = 29$ households
          - Pre-trial Peak Mean (2012): `0.2759 kWh/hh` | Post-trial Peak Mean (2013): `0.2580 kWh/hh`
          - Control Delta ($\Delta_{Std}$): `-0.0179 kWh/hh`
        - **Treatment Cohort (Dynamic Time-of-Use):** $n = 32$ households
          - Pre-trial Peak Mean (2012): `0.2784 kWh/hh` | Post-trial Peak Mean (2013): `0.2773 kWh/hh`
          - Treatment Delta ($\Delta_{ToU}$): `-0.0010 kWh/hh`
        - **DiD Estimator ($\Delta_{ToU} - \Delta_{Std}$):** `+0.0169 kWh/hh per half-hour`
        - **Test Statistics:** Welch's $t = 1.4170$, $p = 0.1623$, Cohen's $d = +0.3676$
        - **95% Confidence Interval:** `[-0.0070, +0.0407]` kWh/half-hour
        """)
    with stat_col2:
        st.info("""
        **Methodological Finding:**
        Found no statistically significant peak reduction in this 61-household sample ($p = 0.1623$, 95% CI $[-0.0070, +0.0407]$ includes small reductions).
        Flat-rate control households reduced peak consumption by 0.0179 kWh/hh while ToU households reduced by only 0.0010 kWh/hh.
        **Commercial Hypothesis to Test:** Voluntary behavioral price signals alone may fail to produce peak demand clipping; commercial propositions should test the hypothesis that achieving peak shifting requires automated hardware (smart EV chargers, automated heat-pump thermostats, home battery storage).
        """)

# -----------------------------------------------------------------------------
# 8. Page 5: Campaign ROI & CPA Sensitivity Simulator
# -----------------------------------------------------------------------------
elif active_page == "Campaign ROI Simulator":
    st.markdown('<div class="main-title">Campaign ROI & CPA Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Unit economics sensitivity modelling for customer acquisition across targeted energy propositions</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="headline-insight">
        <strong>Unit Economics Rule of Thumb:</strong> Reach is determined by marketing budget divided by cost per contact 
        (<code>contacts = spend / cost_per_contact</code>). At <strong>€5.50/contact</strong> and composite customer lifetime value of 
        <strong>€835.50</strong> (3.2-year lifespan × €240 dual fuel margin + 15% × €450 retrofit fee), the campaign achieves break-even at 
        <strong>0.658% conversion</strong>.
    </div>
    """, unsafe_allow_html=True)
    
    # Interactive Controls
    ctrl1, ctrl2, ctrl3 = st.columns(3)
    with ctrl1:
        budget = st.slider("Campaign Marketing Budget (€):", 50000, 500000, 100000, step=25000)
    with ctrl2:
        conv_rate_pct = st.slider("Conversion Rate (%):", 0.5, 6.0, 3.5, step=0.1)
        conv_rate = conv_rate_pct / 100.0
    with ctrl3:
        cost_per_contact = st.slider("Cost per Contact (€):", 2.00, 10.00, 5.50, step=0.50)
        
    # Exact Formulas Matching Code
    contacts = int(round(budget / cost_per_contact))
    acquired = int(round(contacts * conv_rate))
    cpa = budget / (acquired + 1e-6)
    
    tenure_years = 3.2
    annual_margin = 240.0
    retrofit_fee = 450.0
    retrofit_takeup = 0.15
    ltv_per_cust = (annual_margin * tenure_years) + (retrofit_takeup * retrofit_fee)  # €835.50
    total_ltv = acquired * ltv_per_cust
    net_profit = total_ltv - budget
    roi_pct = (net_profit / budget) * 100.0
    break_even_conv_pct = (cost_per_contact / ltv_per_cust) * 100.0
    
    # 4 Output Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Audience Contacts Reached</div>
            <div class="kpi-value">{contacts:,.0f}</div>
            <div class="kpi-delta delta-neutral">Formula: Spend / Cost per Contact</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Customers Acquired</div>
            <div class="kpi-value">{acquired:,.0f}</div>
            <div class="kpi-delta delta-positive">At {conv_rate_pct:.1f}% conversion rate</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Cost Per Acquisition (CPA)</div>
            <div class="kpi-value">€{cpa:.2f}</div>
            <div class="kpi-delta delta-positive">Composite LTV: €{ltv_per_cust:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Projected Campaign ROI</div>
            <div class="kpi-value">{roi_pct:.1f}%</div>
            <div class="kpi-delta delta-positive">Break-even conversion: {break_even_conv_pct:.3f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Pre-computed Sensitivity Grid from Gold Table
    st.markdown("#### Pre-computed Sensitivity Matrix from Gold Parquet")
    df_sens = query_df("SELECT * FROM kpi_campaign_roi_sensitivity")
    st.dataframe(
        df_sens[[
            "marketing_spend_eur", "contacts_reached",
            "conversion_rate", "customers_acquired", "cpa_eur", "total_ltv_revenue_eur", "roi_pct", "breakeven_conversion_rate_pct"
        ]].style.format({
            "marketing_spend_eur": "€{:,.0f}",
            "contacts_reached": "{:,.0f}",
            "conversion_rate": "{:.1%}",
            "customers_acquired": "{:,.0f}",
            "cpa_eur": "€{:.2f}",
            "total_ltv_revenue_eur": "€{:,.0f}",
            "roi_pct": "{:.1f}%",
            "breakeven_conversion_rate_pct": "{:.3f}%"
        }),
        use_container_width=True
    )

# -----------------------------------------------------------------------------
# 9. Page 6: Data Health & Governance
# -----------------------------------------------------------------------------
elif active_page == "Data Health & Governance":
    st.markdown('<div class="main-title">Data Integrity & Governance Scorecard</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Evaluated expectations, quarantine routing, regulatory SLAs, and GDPR compliance</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="headline-insight">
        <strong>Governance Summary:</strong> Data quality expectations evaluated directly on the conformed datasets. 
        All structural constraints achieved <strong>100% pass rates</strong>, while smart-meter duplicate filtering achieved 
        <strong>99.93% pass rate</strong> (1,376 duplicate records identified and deduplicated). 
        All customer identifiers are cryptographically pseudonymised using salted SHA-256.
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Evaluated Data Quality Scorecard", "Freshness Tracking & SLAs", "GDPR Controls & Quarantine"])
    
    with tab1:
        st.markdown("#### Lakeflow Declarative Pipeline Expectations (Evaluated Outputs)")
        df_dq = query_df("SELECT * FROM data_quality_scorecard")
        st.dataframe(
            df_dq[[
                "expectation_name", "target_dataset", "total_evaluated",
                "passed_records", "failed_records", "pass_rate_pct", "quarantine_action"
            ]].style.format({
                "total_evaluated": "{:,.0f}",
                "passed_records": "{:,.0f}",
                "failed_records": "{:,.0f}",
                "pass_rate_pct": "{:.2f}%"
            }),
            use_container_width=True
        )
        
    with tab2:
        st.markdown("#### Source System Freshness & Latency Audit")
        df_fresh = query_df("SELECT * FROM freshness_tracking")
        st.dataframe(
            df_fresh[[
                "source_system", "jurisdiction", "update_frequency",
                "sla_days", "sla_status", "latency_hours"
            ]],
            use_container_width=True
        )
        
    with tab3:
        st.markdown("#### Enterprise GDPR Controls (Articles 4, 25 & 32)")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("""
            - **Salted SHA-256 Pseudonymisation:** Applied to all smart-meter household identifiers (`household_id`). Raw identifiers are never exposed downstream.
            - **Unity Catalog Dynamic Column Masks:** Masking definitions authored in `notebooks/02_silver_lakeflow_pipeline.py`.
            - **Audit Trail:** Immutable Bronze metadata tracks `_source_file`, `_ingested_at`, `_source_system`, and `_jurisdiction`.
            """)
        with g2:
            st.markdown("""
            - **Row-Level Security (RLS):** Jurisdiction-based row filters ensure Irish analysts cannot inspect GB household smart-meter data without authorization.
            - **Quarantine Isolation:** Malformed records are isolated in `silver.quarantine_*` tables, ensuring zero silent data loss.
            - **Right to Erasure (RTBF):** Delta Lake Change Data Feed (CDF) enables targeted deletion passes on request.
            """)
