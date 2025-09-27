# modules/ops_it.py
import datetime as _dt
import streamlit as st
from artifact_registry import save_artifact, get_latest, approve_artifact

def _pid():
    return (st.session_state.get("current_project_id")
            or st.session_state.get("active_project_id")
            or "P-DEMO")

def _day():
    d = st.date_input("Ops day", _dt.date.today(), key="it_ops_day")
    return d.isoformat()

def run(T=None):
    ops_mode = (T or {}).get("ops_mode") or st.session_state.get("ops_mode", "daily_ops")
    day = _day()
    phase_id = f"DAY-{day}"
    st.caption(f"Sub-mode: **{ops_mode}**  •  Phase: `{phase_id}`")

    # -------- KPIs ----------
    st.subheader("Daily KPIs")
    c = st.columns(6)
    with c[0]: tot_contacts = st.number_input("Contacts", 0, step=1, value=0)
    with c[1]: answered = st.number_input("Answered in SLA (%)", 0.0, 100.0, 90.0, 0.1)
    with c[2]: aht_sec   = st.number_input("AHT (sec)", 0, step=1, value=300)
    with c[3]: fcr_pct   = st.number_input("FCR (%)", 0.0, 100.0, 75.0, 0.1)
    with c[4]: abandon   = st.number_input("Abandon (%)", 0.0, 100.0, 3.0, 0.1)
    with c[5]: uptime    = st.number_input("Uptime (%)", 0.0, 100.0, 99.5, 0.1)
    backlog = st.number_input("Backlog (tickets)", 0, step=1, value=0)

    if st.button("Save KPI Snapshot"):
        save_artifact(_pid(), phase_id, "PMO", "KPI_Snapshot", {
            "date_utc": day, "window": "day",
            "tot_contacts": tot_contacts, "answered_in_sla_pct": answered,
            "aht_sec": aht_sec, "fcr_pct": fcr_pct, "abandon_pct": abandon,
            "qa_pass_pct": None, "backlog": backlog, "uptime_pct": uptime,
            "notes": "Pending supervisor review"
        }, status="Pending")
        st.success("Saved KPI_Snapshot (Pending).")

    st.divider()

    # -------- Shift Handover ----------
    st.subheader("Shift Handover")
    notes = st.text_area("Notes / top issues")
    if st.button("Save Shift Handover (End)"):
        save_artifact(_pid(), phase_id, "Ops", "Shift_Handover", {
            "shift_id": f"{day}-A", "type": "End",
            "checklist": [], "notes": notes, "top_issues": []
        }, status="Pending")
        st.success("Saved Shift_Handover (Pending).")

    st.divider()

    # -------- QA / QC ----------
    st.subheader("QA / QC (sample check)")
    agent = st.text_input("Agent ID")
    acc   = st.slider("Accuracy", 0, 100, 90)
    proc  = st.slider("Process adherence", 0, 100, 88)
    soft  = st.slider("Soft skills", 0, 100, 92)
    score = int(0.4*acc + 0.3*proc + 0.3*soft)
    st.metric("Score", score)
    pass_threshold = 80

    if st.button("Save QA Scorecard"):
        save_artifact(_pid(), phase_id, "Quality", "QA_Scorecard", {
            "date_utc": day, "agent_id": agent,
            "dimensions": [
                {"name":"Accuracy","weight":0.4,"score":acc},
                {"name":"Process Adherence","weight":0.3,"score":proc},
                {"name":"Soft Skills","weight":0.3,"score":soft},
            ],
            "pass_threshold": pass_threshold, "pass": score >= pass_threshold
        }, status="Pending")
        st.success("Saved QA_Scorecard (Pending).")

    return {
        "day": day, "contacts": tot_contacts, "aht_sec": aht_sec,
        "fcr_pct": fcr_pct, "uptime_pct": uptime, "backlog": backlog
    }
