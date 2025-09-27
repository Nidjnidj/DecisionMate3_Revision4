# cost.py (same folder as app.py)
import streamlit as st
from artifact_registry import save_artifact, approve_artifact, get_latest

def run(stage: str):
    st.subheader(f"Cost / Economics — {stage}")

    project_id  = st.session_state.get("current_project_id", "P-DEMO")
    phase_id    = st.session_state.get("current_phase_id", "PH-FEL1")

    wacc = st.number_input("WACC (decimal)", value=0.1, min_value=0.0, max_value=1.0, step=0.01)
    capex1 = st.number_input("CAPEX — Procurement", value=150000, step=1000)
    capex2 = st.number_input("CAPEX — Construction", value=120000, step=1000)

    if st.button("Save Cost Model (Draft)"):
        cashflow = [
            {"date": "2026-01-15", "outflow": capex1, "inflow": 0},
            {"date": "2026-02-20", "outflow": capex2, "inflow": 0},
        ]
        save_artifact(project_id, phase_id, "Finance", "Cost_Model", {
            "capex_breakdown": [{"wbs_id": "1.1", "cost": capex1}, {"wbs_id": "1.2", "cost": capex2}],
            "opex_breakdown": [], "cashflow": cashflow, "wacc": wacc
        }, status="Draft")
        st.success("Cost Model saved (Draft).")

    rec = get_latest(project_id, "Cost_Model", phase_id)
    if rec:
        st.caption(f"Latest Cost Model status: {rec.get('status','?')}")
        if rec.get("status") != "Approved" and st.button("Approve Cost Model"):
            approve_artifact(project_id, rec["artifact_id"])
            st.success("Cost Model Approved.")
