# modules/it_schedule.py
from __future__ import annotations
import streamlit as st
from datetime import date, timedelta
import math
from typing import List, Dict, Any
from utils.artifact_bridge import save_artifact, get_latest, approve_artifact
from modules.it_contracts import IT_ENGINEERING, IT_BUSINESS_CASE, IT_SCHEDULE, ITSprintSchedule

def _compute_releases(start: date, sprint_weeks: int, sprints: int) -> List[str]:
    d = start
    releases = []
    for _ in range(sprints):
        d = d + timedelta(weeks=sprint_weeks)
        releases.append(d.isoformat())
    return releases

def run():
    st.subheader("IT · Schedule")
    project_id = st.session_state.get("active_project_id", "demo-project")

    eng = get_latest(project_id, IT_ENGINEERING)
    bc  = get_latest(project_id, IT_BUSINESS_CASE)
    if not eng:
        st.warning("No Engineering artifact found. Please complete Engineering first.")
        return
    if not eng.get("approved"):
        st.warning("Engineering exists but is not Approved yet. Approve it before Schedule.")
        return

    total_sp = int(eng["data"].get("backlog_story_points", 200))
    st.info(f"Upstream backlog: **{total_sp} SP**")

    methodology = st.selectbox("Methodology", ["Scrum","Kanban"], index=0)
    sprint_len = st.number_input("Sprint length (weeks)", min_value=1, value=2, step=1)
    velocity = st.number_input("Velocity (story points per sprint)", min_value=1, value=40, step=5)
    start_iso = st.date_input("Start date", value=date.today()).isoformat()

    if methodology == "Scrum":
        sprints = max(1, math.ceil(total_sp / int(velocity)))
        releases = _compute_releases(date.fromisoformat(start_iso), int(sprint_len), sprints)
    else:
        # Simple Kanban placeholder: treat as 4-week increments
        sprints = max(1, math.ceil(total_sp / int(velocity)))
        releases = _compute_releases(date.fromisoformat(start_iso), 4, sprints)

    st.write(f"**Calculated sprints:** {sprints}")
    st.write("**Release dates:**")
    for i, r in enumerate(releases, 1):
        st.write(f"- Sprint {i}: {r}")

    st.markdown("**Milestones**")
    ms_rows = st.number_input("How many milestones?", min_value=0, value=2, step=1)
    milestones = []
    for i in range(ms_rows):
        with st.expander(f"Milestone #{i+1}", expanded=(i==0)):
            name = st.text_input("Name", value=("MVP" if i==0 else "GA"), key=f"it_ms_name_{i}")
            when = st.date_input("Date", value=date.fromisoformat(releases[min(i,len(releases)-1)]), key=f"it_ms_date_{i}")
            milestones.append({"name": name, "date": when.isoformat()})

    st.markdown("**Resource plan** (role, FTE)")
    r_rows = st.number_input("How many resource roles?", min_value=1, value=3, step=1)
    resource_plan=[]
    for i in range(r_rows):
        with st.expander(f"Role #{i+1}", expanded=(i<2)):
            role = st.text_input("Role", value=("Backend Dev" if i==0 else ("Frontend Dev" if i==1 else "QA")), key=f"it_sched_role_{i}")
            fte  = st.number_input("FTE", min_value=0.0, value=1.0, step=0.1, key=f"it_sched_fte_{i}")
            resource_plan.append({"role": role, "FTE": float(fte)})

    if st.button("Save Schedule", type="primary"):
        payload = ITSprintSchedule(
            methodology=methodology,
            sprint_length_weeks=int(sprint_len),
            velocity_sp_per_sprint=int(velocity),
            total_story_points=total_sp,
            number_of_sprints=int(sprints),
            start_date=start_iso,
            release_dates=releases,
            milestones=milestones,
            resource_plan=resource_plan,
            upstream_refs=[eng["id"], IT_ENGINEERING, (bc["id"] if bc else ""), IT_BUSINESS_CASE],
        ).to_dict()
        rec = save_artifact(project_id, IT_SCHEDULE, payload, stage="Schedule")
        st.success(f"Saved Schedule (id: {rec['id']}).")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Approve Schedule ✅"):
            if approve_artifact(project_id, IT_SCHEDULE):
                st.success("Schedule approved.")
            else:
                st.warning("Nothing to approve yet.")
    with c2:
        st.info("Next: IT · Cost")
