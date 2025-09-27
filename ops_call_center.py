# ops_call_center.py
import streamlit as st
from artifact_registry import save_artifact, approve_artifact, get_latest, publish_event
import datetime as dt

def _ops_day_phase_id(date_str: str | None = None) -> str:
    d = date_str or dt.date.today().isoformat()
    return f"DAY-{d}"

def _kpi_box(title, value, help_txt=""):
    c = st.container()
    with c:
        st.metric(title, value if value is not None else "—", help_txt)
    return c

def _append_ticket_ui(project_id, phase_id):
    st.subheader("Add Ticket (quick)")
    c1, c2, c3, c4 = st.columns(4)
    with c1: ticket_id = st.text_input("Ticket ID", key="cc_ticket_id")
    with c2: agent_id  = st.text_input("Agent ID", key="cc_agent_id")
    with c3: queue     = st.selectbox("Queue", ["voice","chat","email"], key="cc_queue")
    with c4: priority  = st.selectbox("Priority", ["Normal","P2","P1"], key="cc_prio")
    c5, c6, c7 = st.columns(3)
    now_iso = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with c5: opened_at   = st.text_input("Opened (ISO)", value=now_iso, key="cc_opened")
    with c6: answered_at = st.text_input("Answered (ISO)", value=now_iso, key="cc_answered")
    with c7: closed_at   = st.text_input("Closed (ISO)", value=now_iso, key="cc_closed")
    c8, c9, c10 = st.columns(3)
    with c8: talk = st.number_input("Talk sec", value=180, min_value=0)
    with c9: hold = st.number_input("Hold sec", value=20, min_value=0)
    with c10: acw = st.number_input("ACW sec", value=40, min_value=0)
    reason = st.text_input("Contact reason", value="General")
    sla = st.number_input("SLA target sec (answer)", value=30, min_value=0)

    if st.button("Save Ticket & Close"):
        rec = save_artifact(project_id, phase_id, "Delivery", "Ticket_Log", {
            "date_utc": dt.date.today().isoformat(),
            "queue": queue, "ticket_id": ticket_id, "agent_id": agent_id, "priority": priority,
            "opened_at": opened_at, "answered_at": answered_at, "closed_at": closed_at,
            "handle_times": {"talk_sec":talk, "hold_sec":hold, "acw_sec":acw},
            "sla_target_sec": sla, "first_contact_resolved": True,
            "contact_reason": reason, "kb_articles_used": []
        }, status="Draft")
        # Emit event so sampler can create a QA card
        publish_event(project_id, "ticket_closed", {
            "ticket_id": ticket_id, "agent_id": agent_id, "queue": queue,
            "closed_at": closed_at, "priority": priority
        })
        st.success("Ticket saved; QA sampling event emitted.")

def _qa_scoring_ui(project_id, phase_id):
    st.subheader("QA/QC")
    t_id = st.text_input("Ticket to score", key="qa_ticket")
    a_id = st.text_input("Agent", key="qa_agent")
    st.caption("Enter weighted scores (0–100)")
    colA, colB, colC = st.columns(3)
    with colA: s1 = st.slider("Process Adherence (30%)", 0, 100, 80)
    with colB: s2 = st.slider("Accuracy (40%)", 0, 100, 85)
    with colC: s3 = st.slider("Soft Skills (30%)", 0, 100, 90)
    total = int(round(0.3*s1 + 0.4*s2 + 0.3*s3))
    st.metric("Total", total)
    pass_th = st.number_input("Pass threshold", 80, 100, 80, step=1)
    if st.button("Save QA Score"):
        rec = save_artifact(project_id, phase_id, "Quality", "QA_Scorecard", {
            "date_utc": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "ticket_id": t_id, "agent_id": a_id,
            "dimensions": [
                {"name":"Process Adherence","weight":0.3,"score":s1},
                {"name":"Accuracy","weight":0.4,"score":s2},
                {"name":"Soft Skills","weight":0.3,"score":s3},
            ],
            "total_score": total, "pass_threshold": pass_th, "pass": total >= pass_th
        }, status="Pending")
        publish_event(project_id, "qa_scored", {
            "ticket_id": t_id, "agent_id": a_id, "total_score": total, "pass": total >= pass_th
        })
        st.success("QA saved; coaching trigger evaluated.")

def _handover_ui(project_id, phase_id):
    st.subheader("Shift Handover")
    shift_id = st.text_input("Shift ID (e.g., 2025-08-20_A)", value=f"{dt.date.today()}_A")
    with st.expander("Start of Shift"):
        sup = st.text_input("Supervisor (start)")
        start_ok = st.checkbox("Systems healthy")
        if st.button("Approve Start Handover"):
            save_artifact(project_id, phase_id, "Ops", "Shift_Handover", {
                "shift_id": shift_id, "type": "Start",
                "systems_health": start_ok, "signoff_incoming": sup
            }, status="Approved")
            st.success("Start handover approved.")
    with st.expander("End of Shift"):
        sup2 = st.text_input("Supervisor (end)")
        notes = st.text_area("Notes", "")
        if st.button("Emit Shift End & Create Pending Handover"):
            publish_event(project_id, "shift_ended", {"shift_id": shift_id, "date": dt.date.today().isoformat()})
            st.success("Event emitted; Pending End handover created.")
        if st.button("Approve Latest End Handover"):
            rec = get_latest(project_id, "Shift_Handover", phase_id)
            if rec:
                approve_artifact(project_id, rec["artifact_id"])
                st.success("End handover approved.")

def _reports_ui(project_id, phase_id):
    st.subheader("Reports")
    # Minimal KPI card using the latest snapshot if any
    snap = get_latest(project_id, "KPI_Snapshot", phase_id)
    d = (snap or {}).get("data", {})
    c1, c2, c3, c4 = st.columns(4)
    _kpi_box("SLA %", d.get("answered_in_sla_pct"))
    _kpi_box("AHT (sec)", d.get("aht_sec"))
    _kpi_box("FCR %", d.get("fcr_pct"))
    _kpi_box("QA Pass %", d.get("qa_pass_pct"))
    if st.button("Emit Daily Rollup"):
        publish_event(project_id, "daily_rollup", {"date": dt.date.today().isoformat()})
        st.success("Daily rollup event emitted (creates Pending KPI snapshot).")

def run(T=None):
    st.title("📞 Daily Operations — Call Center QA/QC")
    project_id = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    phase_id = _ops_day_phase_id()
    st.caption(f"Project: {project_id} • Ops Day: {phase_id}")

    tabs = st.tabs(["Wallboard", "QA/QC", "Coaching", "Handover", "Reports"])
    with tabs[0]:
        st.subheader("Wallboard (demo)")
        _kpi_box("Backlog", 0)
        _kpi_box("SLA at risk", 0)
        st.divider()
        _append_ticket_ui(project_id, phase_id)

    with tabs[1]:
        _qa_scoring_ui(project_id, phase_id)

    with tabs[2]:
        st.subheader("Coaching")
        st.caption("Approve Coaching Plans created from QA fails.")
        rec = get_latest(project_id, "Coaching_Plan", phase_id)
        if rec and rec.get("status") == "Pending":
            st.write("Pending Coaching Plan for:", rec["data"].get("agent_id"))
            if st.button("Approve Coaching Plan"):
                approve_artifact(project_id, rec["artifact_id"]); st.success("Approved.")
        else:
            st.caption("No pending plans right now.")

    with tabs[3]:
        _handover_ui(project_id, phase_id)

    with tabs[4]:
        _reports_ui(project_id, phase_id)
