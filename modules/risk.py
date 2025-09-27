import streamlit as st
from ._common import _ensure_deliverable, _mark_deliverable, _set_artifact_status
from artifact_registry import save_artifact

DELIV_BY_STAGE = {
    "FEL1": "Risk Register Baseline (Risk)",
    "FEL2": "Risk Register Update (Risk)",
    "FEL3": "Risk Response Plan (Risk)",
    "FEL4": "Risk Watchlist (Risk)",
}

ARTIFACT = "Risk_Register"


def run(stage: str):
    st.header("Risk Management")
    deliverable = DELIV_BY_STAGE.get(stage, "Risk Register")

    _ensure_deliverable(stage, deliverable)

    st.text_area("Risks (ID, Title, Likelihood, Impact, Owner)", key=f"risk_tbl_{stage}")

    if st.button("Approve Risk Register"):
        _mark_deliverable(stage, deliverable, "Done")
        _set_artifact_status(ARTIFACT, "Approved")
        st.success("Risk Register approved.")
        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", "PH-FEL1")
        data = {
            "risk_table_raw": st.session_state.get(f"risk_tbl_{stage}", ""),
        }
        save_artifact(project_id, phase_id, "Risk", ARTIFACT, data, status="Approved")
