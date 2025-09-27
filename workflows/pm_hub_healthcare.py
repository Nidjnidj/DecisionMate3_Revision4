import streamlit as st
import datetime as _dt
from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel

def render(T=None):
    st.subheader("📊 PM Hub — Healthcare")

    project_id = st.session_state.get("current_project_id", "P-HEALTH-DEMO")
    phase_id   = st.session_state.get("current_phase_id", "PH-FEL1")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        occupancy_pct = st.slider("Bed occupancy (%)", 0, 100, 82)
        st.metric("Occupancy", f"{occupancy_pct}%")
    with col2:
        er_wait_min = st.number_input("ER median wait (min)", 0, 720, 38)
        st.metric("ER Wait", f"{er_wait_min} min")
    with col3:
        los_days = st.number_input("Avg LOS (days)", 0.0, 60.0, 4.6, step=0.1)
        st.metric("Avg LOS", f"{los_days:.1f} d")
    with col4:
        readmit_pct = st.number_input("30-day readmit (%)", 0.0, 100.0, 11.2, step=0.1)
        st.metric("Readmission", f"{readmit_pct:.1f}%")

    st.divider()
    st.markdown("### Service Line Volumes (Month-to-Date)")
    svc = st.data_editor(
        [
            {"Service": "Emergency",     "Visits": 4120},
            {"Service": "Surgery (OR)",  "Cases": 820},
            {"Service": "Inpatient",     "Discharges": 1350},
            {"Service": "Outpatient",    "Encounters": 9800},
        ],
        num_rows="dynamic",
        use_container_width=True,
        key="hc_pm_lines",
    )
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()
    # return snapshot so autosave engine can persist it
    return {
        "project_id": project_id,
        "phase_id": phase_id,
        "date": _dt.date.today().isoformat(),
        "kpis": {
            "occupancy_pct": occupancy_pct,
            "er_wait_min": er_wait_min,
            "los_days": los_days,
            "readmission_pct": readmit_pct,
        },
        "service_lines": svc,
    }

# optional alias (your app will try 'render' first)
def run(T=None):  # noqa
    return render(T)
