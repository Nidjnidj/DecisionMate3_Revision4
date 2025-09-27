import streamlit as st
import datetime as _dt

def _daily_ops():
    st.markdown("### Daily Ops — Hospital")

    colA, colB, colC, colD = st.columns(4)
    with colA:
        ops_day = st.date_input("Ops day", value=_dt.date.today())
    with colB:
        staffed_beds = st.number_input("Staffed beds", 0, 5000, 420)
    with colC:
        occupied_beds = st.number_input("Occupied beds", 0, 5000, 356)
    with colD:
        icu_occupied = st.number_input("ICU occupied", 0, 1000, 28)

    occ = round(100.0 * (occupied_beds / staffed_beds), 1) if staffed_beds else 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Occupancy", f"{occ:.1f}%")
    with col2:
        er_wait = st.number_input("ER median wait (min)", 0, 720, 42)
        st.metric("ER Wait", f"{er_wait} min")
    with col3:
        lwbs = st.number_input("LWBS (count)", 0, 10000, 31)  # Left Without Being Seen
        st.metric("LWBS", lwbs)
    with col4:
        staff_coverage = st.slider("Staffing coverage (%)", 0, 120, 93)
        st.metric("Staff Coverage", f"{staff_coverage}%")

    st.markdown("#### Top Issues")
    issues = st.data_editor(
        [
            {"Area": "ED",  "Issue": "CT downtime",       "Owner": "Radiology",      "ETA": "2h"},
            {"Area": "ICU", "Issue": "Vent shortage",     "Owner": "Respiratory",    "ETA": "EOD"},
        ],
        num_rows="dynamic",
        key="hc_ops_issues",
        use_container_width=True,
    )

    return {
        "date": ops_day.isoformat(),
        "kpis": {
            "occupancy_pct": occ,
            "er_wait_min": er_wait,
            "lwbs": lwbs,
            "staff_coverage_pct": staff_coverage,
            "icu_occupied": icu_occupied,
            "occupied_beds": occupied_beds,
            "staffed_beds": staffed_beds,
        },
        "issues": issues,
    }

def _small_projects():
    st.markdown("### Small Projects — Clinical Improvements (PDSA)")
    items = st.data_editor(
        [
            {"Project": "Triage fast-track",              "Owner": "ED Nurse Mgr", "Due": "2025-09-15", "Status": "In Progress"},
            {"Project": "OR first-case on-time start",    "Owner": "OR Director",  "Due": "2025-10-01", "Status": "Not Started"},
        ],
        num_rows="dynamic",
        key="hc_ops_smallprojects",
        use_container_width=True,
    )
    return {"small_projects": items}

def _call_center():
    st.markdown("### Patient Access / Call Center")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        calls = st.number_input("Calls received", 0, 100000, 3200)
    with col2:
        ans_pct = st.slider("Answered in SLA (%)", 0, 100, 86)
    with col3:
        aht_sec = st.number_input("AHT (sec)", 0, 3600, 240)
    with col4:
        abandon = st.slider("Abandon (%)", 0, 100, 4)
    return {"kpis": {
        "calls_received": calls,
        "answered_in_sla_pct": ans_pct,
        "aht_sec": aht_sec,
        "abandon_pct": abandon,
    }}

def render(T=None):
    ops_mode = (T or {}).get("ops_mode") or st.session_state.get("ops_mode", "daily_ops")
    st.subheader("🏥 Ops Hub — Healthcare")
    st.caption(f"Mode: **{ops_mode}**")

    if ops_mode == "small_projects":
        return _small_projects()
    if ops_mode == "call_center":
        return _call_center()
    return _daily_ops()

def run(T=None):  # alias
    return render(T)
