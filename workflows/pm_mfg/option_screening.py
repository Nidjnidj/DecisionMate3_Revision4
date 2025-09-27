import streamlit as st
import pandas as pd
import numpy as np

def run():
    st.header("Option Screening")
    st.caption("Compare 2–4 factory options on CAPEX/OPEX/lead time/footprint. Lower is better for all scores below.")

    if "mfg_opt" not in st.session_state:
        st.session_state.mfg_opt = pd.DataFrame([
            {"Option": "Brownfield", "CAPEX": 22_000_000, "OPEX": 8_000_000, "LeadMonths": 9,  "Footprint_m2": 18000},
            {"Option": "Greenfield", "CAPEX": 28_000_000, "OPEX": 6_500_000, "LeadMonths": 14, "Footprint_m2": 22000},
        ])

    df = st.data_editor(st.session_state.mfg_opt, num_rows="dynamic", use_container_width=True, key="opt_editor")
    st.session_state.mfg_opt = df

    d = df.copy()
    for c in ("CAPEX","OPEX","LeadMonths","Footprint_m2"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)

    # Normalize 0..1 (min=best), weighted score
    def norm(x): 
        if x.max() == x.min(): 
            return np.zeros(len(x))
        return (x - x.min())/(x.max() - x.min())
    W = {"CAPEX":0.35, "OPEX":0.35, "LeadMonths":0.2, "Footprint_m2":0.1}
    d["Score"] = (norm(d["CAPEX"])*W["CAPEX"] + norm(d["OPEX"])*W["OPEX"] +
                  norm(d["LeadMonths"])*W["LeadMonths"] + norm(d["Footprint_m2"])*W["Footprint_m2"])
    st.subheader("Ranking")
    st.dataframe(d.sort_values("Score"), use_container_width=True)
    if not d.empty:
        st.success(f"Recommended (lowest score): **{d.sort_values('Score').iloc[0]['Option']}**")
