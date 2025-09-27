import streamlit as st
from artifact_registry import save_artifact

ART = "L2_L3_Schedule_Draft"

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("L2/L3 Schedule Draft")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    tasks = st.text_area("High-level tasks (one per line)", "Concept design\nDesign development\nIFC\nProcure\nBuild")
    rows  = [{"name": t.strip(), "dur_days": 10} for t in tasks.splitlines() if t.strip()]

    if st.button("Save L2_L3_Schedule_Draft (Pending)"):
        save_artifact(pid, phid, "Schedule", ART, {"rows": rows}, status="Pending")
        st.success("Saved.")
