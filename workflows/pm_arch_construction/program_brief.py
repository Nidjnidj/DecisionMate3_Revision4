import re
import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE = "Program_Brief"

def _parse_tags(raw: str) -> list[str]:
    parts = re.split(r"[,\n]+", raw or "")
    return [p.strip() for p in parts if p.strip()]

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("Program Brief")
    project_id = project_id or st.session_state.get("current_project_id","P-AC-DEMO")
    phase_id   = phase_id   or st.session_state.get("current_phase_id","PH-FEL1")

    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("Project name", value=st.session_state.get("proj_name","Untitled"))
        capex_cap = st.number_input("Budget cap (M$)", 0.0, value=50.0)
    with col2:
        gfa = st.number_input("Target GFA (m²)", 0.0, value=12000.0, step=100.0)
        levels = st.number_input("Levels", 1, 100, 6)
    with col3:
        occupancy = st.selectbox("Type", ["Office","Residential","School","Hospital"], index=0)
        target_date = st.date_input("Target Completion")

    scope = st.text_area("Scope summary", "Core & shell; fit-out; siteworks …")
    drivers = st.text_area("Key drivers", "Cost; schedule; sustainability; flexibility …")
    constraints = st.text_area("Constraints", "Zoning; utilities; site access; noise …")

    tags_raw = st.text_input("Stakeholders (comma or newline separated)", "Owner, PMO, Designer")
    stakeholders = _parse_tags(tags_raw)

    payload = {
        "name": name, "budget_musd": capex_cap, "target_gfa_m2": gfa, "levels": int(levels),
        "type": occupancy, "target_completion": str(target_date),
        "scope": scope, "drivers": drivers, "constraints": constraints,
        "stakeholders": stakeholders,
    }

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Draft"):
            save_artifact(project_id, phase_id, "Planning", ART_TYPE, payload, status="Draft")
            st.success("Program_Brief saved (Draft).")
    with c2:
        if st.button("Save & Mark Pending"):
            save_artifact(project_id, phase_id, "Planning", ART_TYPE, payload, status="Pending")
            st.success("Program_Brief saved (Pending).")

    latest = get_latest(project_id, ART_TYPE, phase_id)
    if latest:
        st.caption(f"Latest status: {latest.get('status')}")
