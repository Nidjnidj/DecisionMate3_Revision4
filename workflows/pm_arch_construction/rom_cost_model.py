import streamlit as st
from artifact_registry import save_artifact, get_latest

ART = "ROM_Cost_Model"

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("ROM Cost Snapshot (Class 4→3)")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    gfa_hint = 10000.0
    fp = get_latest(pid, "Footprint_Estimate", phid)
    if fp: gfa_hint = float(fp.get("data", {}).get("gfa_m2", gfa_hint))

    gfa = st.number_input("GFA (m²)", 0.0, value=gfa_hint, step=100.0)
    unit_rate = st.number_input("Unit rate ($/m²)", 0.0, value=1500.0, step=50.0)
    cont_pct  = st.number_input("Contingency (%)", 0.0, 50.0, 10.0)
    total = gfa * unit_rate * (1 + cont_pct/100.0)
    st.metric("ROM CAPEX (USD)", f"{total:,.0f}")

    if st.button("Save ROM_Cost_Model (Pending)"):
        save_artifact(pid, phid, "Finance", ART,
                      {"gfa_m2": gfa, "unit_rate": unit_rate, "contingency_pct": cont_pct, "total": total},
                      status="Pending")
        st.success("Saved.")
