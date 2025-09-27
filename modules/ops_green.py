# modules/ops_green.py
import datetime as _dt
import streamlit as st
from artifact_registry import save_artifact, get_latest, approve_artifact

def _pid():
    return (st.session_state.get("current_project_id")
            or st.session_state.get("active_project_id")
            or "P-DEMO")

def _day():
    d = st.date_input("Ops day", _dt.date.today(), key="green_ops_day")
    return d.isoformat()

def run(T=None):
    day = _day(); phase_id = f"DAY-{day}"
    kind = st.selectbox("Green asset type", ["wind","solar","hydrogen"], key="green_ops_kind")
    st.caption(f"Phase: `{phase_id}`  •  Type: **{kind}**")

    c = st.columns(5)
    if kind == "wind":
        with c[0]: gen = st.number_input("Gen (MWh)", 0.0, step=1.0, value=120.0)
        with c[1]: avail = st.number_input("Availability (%)", 0.0, 100.0, 96.0, 0.1)
        with c[2]: curt = st.number_input("Curtailment (%)", 0.0, 100.0, 1.5, 0.1)
        with c[3]: alarms = st.number_input("Turbine alarms", 0, step=1, value=3)
        with c[4]: hse = st.number_input("HSE recordables", 0, step=1, value=0)
    elif kind == "solar":
        with c[0]: gen = st.number_input("Gen (MWh)", 0.0, step=1.0, value=95.0)
        with c[1]: avail = st.number_input("Availability (%)", 0.0, 100.0, 98.0, 0.1)
        with c[2]: curt = st.number_input("Curtailment (%)", 0.0, 100.0, 0.5, 0.1)
        with c[3]: alarms = st.number_input("Inverter trips", 0, step=1, value=1)
        with c[4]: hse = st.number_input("HSE recordables", 0, step=1, value=0)
    else:
        with c[0]: gen = st.number_input("H2 produced (t)", 0.0, step=0.1, value=45.0)
        with c[1]: avail = st.number_input("Electrolyzer uptime (%)", 0.0, 100.0, 94.0, 0.1)
        with c[2]: curt = st.number_input("Power curtailment (%)", 0.0, 100.0, 2.0, 0.1)
        with c[3]: alarms = st.number_input("Trips / alarms", 0, step=1, value=2)
        with c[4]: hse = st.number_input("HSE recordables", 0, step=1, value=0)

    notes = st.text_area("Notes")

    if st.button("Save KPI Snapshot"):
        save_artifact(_pid(), phase_id, "PMO", "KPI_Snapshot", {
            "date_utc": day, "window": "day",
            "gen_value": gen, "availability_pct": avail,
            "curtailment_pct": curt, "alarms": alarms, "hse_recordables": hse,
            "asset_type": kind, "notes": notes
        }, status="Pending")
        st.success("Saved KPI_Snapshot (Pending).")

    # optional quick shift handover
    if st.button("Save Shift Handover (End)"):
        save_artifact(_pid(), phase_id, "Ops", "Shift_Handover", {
            "shift_id": f"{day}-G", "type": "End", "notes": notes
        }, status="Pending")
        st.success("Saved Shift_Handover (Pending).")

    return {"day": day, "type": kind, "gen": gen, "availability_pct": avail, "curtailment_pct": curt}
