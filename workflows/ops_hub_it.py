# workflows/ops_hub_it.py
import streamlit as st
import datetime as dt

def render(T=None):
    """IT Ops Hub (NOC/Service Desk style). Returns a dict snapshot."""
    T = T or {}
    sub_mode = T.get("ops_mode", "daily_ops")

    st.subheader("🛠 Ops — IT")

    if sub_mode == "daily_ops":
        st.markdown("### 🖥️ Daily Ops — IT")
        d = st.date_input("Ops day", value=dt.date.today(), key="it_ops_day")

        with st.expander("⚙️ Settings / Alerts", expanded=False):
            st.checkbox("Page when P1 opened", key="it_alert_p1")
            st.checkbox("Alert when SLA < 95%", key="it_alert_sla")

        col1, col2, col3, col4 = st.columns(4)
        with col1: opened = st.number_input("Tickets Opened", min_value=0, value=120, step=1, key="it_opened")
        with col2: resolved = st.number_input("Tickets Resolved", min_value=0, value=115, step=1, key="it_resolved")
        with col3: sla = st.number_input("SLA Met (%)", min_value=0.0, max_value=100.0, value=93.5, step=0.1, key="it_sla")
        with col4: backlog = st.number_input("Backlog", min_value=0, value=240, step=1, key="it_backlog")

        st.divider()
        t1, t2 = st.tabs(["Queues", "Incidents / Changes"])
        with t1:
            st.data_editor([
                {"Queue": "Service Desk", "Open": 62, "AHT_min": 7.8, "FCR_%": 74.0},
                {"Queue": "Email",        "Open": 28, "AHT_min": 5.1, "FCR_%": 60.0},
                {"Queue": "Chat",         "Open": 30, "AHT_min": 4.6, "FCR_%": 69.0},
            ], key="it_queues", num_rows="dynamic")
        with t2:
            st.data_editor([
                {"Type": "P1 Incident", "Ref": "INC-1011", "Status": "Investigating", "Owner": "NOC"},
                {"Type": "Change", "Ref": "CHG-2044", "Status": "Scheduled", "Window": "Fri 22:00"},
            ], key="it_inc", num_rows="dynamic")

        return {
            "ops_mode": sub_mode,
            "date": str(d),
            "tickets_opened": opened,
            "tickets_resolved": resolved,
            "sla_met_pct": sla,
            "backlog": backlog,
        }

    if sub_mode == "small_projects":
        st.markdown("### 🧰 Small Projects — IT")
        tbl = st.data_editor([
            {"ID": "IT-001", "Title": "Deploy SSO for HR", "Owner": "Infra", "Due": "2025-09-15", "Status": "In Progress"},
            {"ID": "IT-002", "Title": "VPN throughput upgrade", "Owner": "Network", "Due": "2025-09-30", "Status": "Planned"},
        ], key="it_sp", num_rows="dynamic")
        return {"ops_mode": sub_mode, "backlog": tbl}

    # call_center: generic KPIs
    st.markdown("### ☎️ Call Center — IT")
    st.data_editor([
        {"Agent": "A-101", "Calls": 42, "AHT_sec": 380, "QA_%": 86.0, "SLA_%": 92.0},
        {"Agent": "A-102", "Calls": 39, "AHT_sec": 420, "QA_%": 88.0, "SLA_%": 90.0},
    ], key="it_cc", num_rows="dynamic")
    return {"ops_mode": sub_mode, "note": "call_center_generic"}
