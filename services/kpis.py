# services/kpis.py
from typing import Dict, Any
import streamlit as st

def render_kpis(kpi_data: dict):
    st.markdown("### 📊 PM Hub — Live KPIs")
    col1, col2, col3 = st.columns(3)

    wbs_nodes = kpi_data.get("WBS_Nodes", 0)
    crit_path = kpi_data.get("Critical_Path_Days", 0)
    capex_items = kpi_data.get("CAPEX_Items", 0)

    col1.metric("WBS nodes", wbs_nodes)
    col2.metric("Critical Path (days)", crit_path)
    col3.metric("CAPEX items", capex_items)

    st.markdown(
        "<div style='margin-bottom: 15px; font-size: 0.9em;'>"
        "Pipeline = guided path: Engineering → Schedule → Cost/Economics. "
        "Uses the same artifacts shown here.</div>",
        unsafe_allow_html=True
    )

def compute_pm_kpis(data: Dict[str, Any]) -> Dict[str, Any]:
    # Minimal placeholders
    capex = float(data.get("capex", 0))
    opex = float(data.get("opex", 0))
    schedule_months = float(data.get("schedule_months", 0))
    risk_score = float(data.get("risk_score", 0))
    return {
        "CAPEX": capex,
        "OPEX": opex,
        "Duration (months)": schedule_months,
        "Risk Index": risk_score,
    }

def compute_ops_kpis(data: Dict[str, Any]) -> Dict[str, Any]:
    uptime = float(data.get("uptime_pct", 0))
    throughput = float(data.get("throughput", 0))
    incidents = int(data.get("incidents", 0))
    return {
        "Uptime %": uptime,
        "Throughput": throughput,
        "Incidents (M/M)": incidents,
    }
