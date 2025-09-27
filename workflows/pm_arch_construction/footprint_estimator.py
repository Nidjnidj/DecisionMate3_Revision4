import streamlit as st
from artifact_registry import save_artifact

ART = "Footprint_Estimate"

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("Footprint Estimator")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    site_area = st.number_input("Site area (m²)", 0.0, value=20000.0, step=100.0)
    footprint= st.number_input("Building footprint (m²)", 0.0, value=5000.0, step=50.0)
    levels   = st.number_input("Levels", 1, 100, 6)
    gfa      = footprint * levels
    sc_ratio = (footprint / site_area) if site_area else 0.0
    st.metric("GFA (m²)", f"{gfa:,.0f}")
    st.metric("Site coverage", f"{sc_ratio*100:.1f}%")

    if st.button("Save Footprint_Estimate (Pending)"):
        save_artifact(pid, phid, "Design", ART, {"site_area_m2":site_area, "footprint_m2":footprint, "levels":int(levels),
                                                 "gfa_m2":gfa, "site_coverage":sc_ratio}, status="Pending")
        st.success("Saved.")
