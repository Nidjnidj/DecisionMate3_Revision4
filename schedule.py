# schedule.py (same folder as app.py)
import streamlit as st
from artifact_registry import save_artifact, approve_artifact, get_latest

def run(stage: str):
    st.subheader(f"Schedule — {stage}")

    project_id  = st.session_state.get("current_project_id", "P-DEMO")
    phase_id    = st.session_state.get("current_phase_id", "PH-FEL1")

    st.markdown("**WBS**")
    default_nodes = [
        {"id": "1",   "parent": None, "name": "Project",      "type": "Project", "phase": stage, "owner": "PM"},
        {"id": "1.1", "parent": "1",  "name": "Procurement",  "type": "WP",      "phase": stage, "owner": "SCM"},
        {"id": "1.2", "parent": "1",  "name": "Construction", "type": "WP",      "phase": stage, "owner": "Construction"},
    ]
    if st.button("Save WBS (Draft)"):
        save_artifact(project_id, phase_id, "Schedule", "WBS", {"nodes": default_nodes}, status="Draft")
        st.success("WBS saved (Draft).")

    rec = get_latest(project_id, "WBS", phase_id)
    if rec:
        st.caption(f"Latest WBS status: {rec.get('status','?')}")
        if rec.get("status") != "Approved" and st.button("Approve WBS"):
            approve_artifact(project_id, rec["artifact_id"])
            st.success("WBS Approved.")

    st.markdown("---")
    st.markdown("**Schedule Network**")
    acts = [
        {"id": "A1", "name": "Order Turbines/Modules", "wbs_id": "1.1", "dur_days": 30, "predecessors": []},
        {"id": "A2", "name": "Install Turbines/Modules","wbs_id": "1.2", "dur_days": 20, "predecessors": ["A1"]},
    ]
    if st.button("Save Schedule Network (Draft)"):
        save_artifact(project_id, phase_id, "Schedule", "Schedule_Network", {
            "activities": acts, "critical_path_ids": ["A1", "A2"],
            "start_date": "2026-01-01", "finish_date": "2026-02-20"
        }, status="Draft")
        st.success("Schedule Network saved (Draft).")

    rec2 = get_latest(project_id, "Schedule_Network", phase_id)
    if rec2:
        st.caption(f"Latest Network status: {rec2.get('status','?')}")
        if rec2.get("status") != "Approved" and st.button("Approve Schedule Network"):
            approve_artifact(project_id, rec2["artifact_id"])
            st.success("Schedule Network Approved.")
