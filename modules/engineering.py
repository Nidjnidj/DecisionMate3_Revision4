import streamlit as st
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
# Embed the legacy simulator inside Engineering
from modules.process_flow_simulation import run as render_simulation
import streamlit as st

from artifact_registry import get_latest, save_artifact   # read Subsurface, persist Eng artifacts
from ._common import (
    ENGINEERING_ARTIFACT_BY_STAGE,
    _ensure_deliverable, _mark_deliverable, _set_artifact_status,
)

# -------------------- simple sizing helpers (engineering sanity) --------------------
def _design_point(series: List[float], p: float = 0.9, uplift: float = 1.15) -> float:
    """P90/peak-ish with a small design uplift."""
    if not series: return 0.0
    arr = np.array(series, dtype=float)
    base = np.quantile(arr[~np.isnan(arr)], p)
    return float(base * uplift)

def _stb_to_m3pd(x_stbpd: float) -> float:
    return float(x_stbpd * 0.158987)  # 1 stb = 0.158987 m³

def _scf_to_nmpd(x_scfpd: float) -> float:
    return float(x_scfpd * 0.0283168)  # 1 scf = 0.0283168 Nm³

def _heater_duty_mw(oil_m3pd: float, dT_C: float = 30.0, rho=820.0, cp_kJkgK=2.1) -> float:
    """Very rough: Q = m*cp*dT ; m[kg/s] from volumetric @ 20°C."""
    kg_per_s = (oil_m3pd / 86400.0) * rho * 1000.0
    kW = kg_per_s * cp_kJkgK * dT_C / 1.0
    return float(kW / 1000.0)

def _compress_power_mw(gas_Nm3pd: float, Pin_bar=10.0, Pout_bar=70.0, T_K=313.0, Z=1.0, k=1.3, eta=0.75):
    """
    Thumb rule for single-stage adiabatic compressor.
    W = (k/(k-1)) * (R*T/Z) * m_dot * [ (P2/P1)^((k-1)/k) - 1 ] / eta
    Convert Nm³/day to mol/s using 1 kmol ≈ 22.414 Nm³ at STP.
    """
    R = 8.314  # kJ/kmol-K
    kmol_per_s = (gas_Nm3pd / 22.414) / 1000.0 / 86400.0
    term = (k/(k-1.0)) * (R*T_K/Z) * kmol_per_s * ( (Pout_bar/Pin_bar)**((k-1.0)/k) - 1.0 )
    kW = term * 1.0 / max(eta, 1e-3)
    return float(kW / 1000.0)

def _cooling_mw(heat_mw: float) -> float:
    return float(max(0.0, heat_mw) * 0.4)  # simple ratio for first-cut

# -------------------- UI --------------------
def run(stage: str):
    st.header("Engineering – Stage Deliverable")

    deliverable = {
        "FEL1": "Reference Case Identification (Engineering)",
        "FEL2": "Concept Selected Package (Engineering)",
        "FEL3": "Defined Concept Package (Engineering)",
        "FEL4": "Execution Concept Package (Engineering)",
    }.get(stage, "Engineering Package")

    artifact = ENGINEERING_ARTIFACT_BY_STAGE.get(stage, "Reference_Case_Identification")
    _ensure_deliverable(stage, deliverable)

    # ---- Pull Subsurface profiles + composition
    project_id = st.session_state.get("current_project_id", "P-DEMO")
    phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")
    rp = get_latest(project_id, "Reservoir_Profiles", phase_id)

    st.subheader("Inputs from Subsurface")
    if not rp:
        st.info("No Reservoir_Profiles artifact yet. Finalize Subsurface first.")
        return

    data = rp.get("data", {}) if isinstance(rp, dict) else {}
    comp = data.get("composition", {})
    cond = data.get("conditions", {})
    dates = data.get("dates", [])
    oil_r = data.get("oil_rate", [])
    gas_r = data.get("gas_rate", [])
    wat_r = data.get("water_rate", [])

    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown("**Rates preview**")
        try:
            df = pd.DataFrame({"date": dates, "oil_rate": oil_r, "gas_rate": gas_r, "water_rate": wat_r})
            st.line_chart(df.set_index("date")[["oil_rate","gas_rate","water_rate"]])
        except Exception:
            st.write("dates / rates not in expected shape")
    with c2:
        st.markdown("**Conditions**")
        st.json(cond or {})
        st.markdown("**Gas zᵢ**")
        st.dataframe(pd.DataFrame(comp.get("gas", [])))
        st.markdown("**Oil pseudo zᵢ**")
        st.dataframe(pd.DataFrame(comp.get("oil", [])))
        if comp.get("inj_gas"):
            st.markdown("**Injected gas zᵢ**")
            st.dataframe(pd.DataFrame(comp.get("inj_gas", [])))

    # ---- Design basis (P90 + uplift)
    st.subheader("Design Basis (first-cut)")
    oil_dp = _design_point(oil_r, 0.9, 1.15)         # stb/d
    gas_dp = _design_point(gas_r, 0.9, 1.15)         # scf/d
    wat_dp = _design_point(wat_r, 0.9, 1.15)         # bwpd
    st.metric("Design oil rate (stb/d)", f"{oil_dp:,.0f}")
    st.metric("Design gas rate (scf/d)", f"{gas_dp:,.0f}")
    st.metric("Design water rate (bwpd)", f"{wat_dp:,.0f}")
    st.markdown("## Process Simulation")
    st.caption("Use the simulator below. It saves PFD, Equipment List, and Utilities Load to the artifact registry.")
    render_simulation(stage)  # simulator already saves Engineering artifacts on Simulate
    st.info("Workflow: Run simulation → it saves Engineering artifacts. Then go to Schedule to create WBS/Network, and to Cost to build Cost Model.")

    st.markdown("### Next steps")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Proceed to Schedule (generate WBS/Network there)"):
            st.session_state["force_open_module"] = "Schedule"
            st.session_state["open_module"] = "Schedule"
            st.session_state["view"] = "Modules"
            st.rerun()
    with col2:
        if st.button("Proceed to Cost (build Cost Model there)"):
            st.session_state["force_open_module"] = "Cost"
            st.session_state["open_module"] = "Cost"
            st.session_state["view"] = "Modules"
            st.rerun()

    # ---- Sizing estimates
    st.subheader("First-cut Sizing & Utilities")
    oil_m3pd = _stb_to_m3pd(oil_dp)
    gas_Nm3pd = _scf_to_nmpd(gas_dp)

    # tweakable assumptions (engineer can adjust)
    Pin  = st.number_input("Comp. suction pressure, bar", 1.0, 100.0, 10.0, 0.5)
    Pout = st.number_input("Comp. discharge pressure, bar", 5.0, 250.0, 70.0, 0.5)
    T_K  = st.number_input("Compression inlet temperature, K", 250.0, 450.0, 313.0, 1.0)
    eta  = st.slider("Compressor efficiency", 0.4, 0.9, 0.75, 0.01)
    dT   = st.slider("Heater ΔT (°C)", 5.0, 80.0, 30.0, 1.0)

    heat_mw  = _heater_duty_mw(oil_m3pd, dT_C=dT)
    comp_mw  = _compress_power_mw(gas_Nm3pd, Pin_bar=Pin, Pout_bar=Pout, T_K=T_K, eta=eta)
    cool_mw  = _cooling_mw(heat_mw) + comp_mw*0.2  # add a bit for inter/aftercoolers

    # ---- Build Equipment List
    equip = [
        {"tag": "HTR-100", "type": "Heater", "service": "Crude preheat", "duty_MW": round(heat_mw,3)},
        {"tag": "SEP-110", "type": "3-Phase Separator", "service": "Primary separation", "oil_m3pd": round(oil_m3pd,1), "water_bwpd": round(wat_dp,0)},
        {"tag": "CMP-200", "type": "Compressor", "service": "Export gas", "power_MW": round(comp_mw,3), "Pin_bar": Pin, "Pout_bar": Pout},
        {"tag": "TRET-120", "type": "Water Treatment", "service": "Produced water", "capacity_bwpd": round(wat_dp,0)},
        {"tag": "STAB-130", "type": "Stabilizer/Flash", "service": "Crude stabilization", "design_stbpd": round(oil_dp,0)},
    ]
    util = {
        "electrical_MW": round(comp_mw + 0.3, 3),   # add 0.3 MW balance-of-plant
        "heating_MW":    round(heat_mw, 3),
        "cooling_MW":    round(cool_mw, 3),
        "nitrogen_norm": 0.02,  # placeholder fractions of gas_dp if you want to expand
        "instrument_air_nm3hr": round(gas_Nm3pd/24.0*0.01, 1),
    }

    st.dataframe(pd.DataFrame(equip))
    cH, cC = st.columns(2)
    with cH: st.metric("Heater duty", f"{heat_mw:.2f} MW")
    with cC: st.metric("Compressor power", f"{comp_mw:.2f} MW")
    st.json(util)
    update_basis_key = f"update_basis_{stage}"
    basis_key = f"eng_basis_{stage}"

    # Update basis if flag is set (before widget is rendered)
    if st.session_state.get(update_basis_key):
        basis_txt = st.session_state.get(basis_key, "")
        basis_txt += (
            "\n\n---\nDesign Basis (from Subsurface)\n"
            f"Oil design {oil_dp:,.0f} stb/d, Gas design {gas_dp:,.0f} scf/d, Water design {wat_dp:,.0f} bwpd\n"
            f"Conditions: {cond}\n"
            f"Gas z_i: {comp.get('gas')}\nOil z_i: {comp.get('oil')}\nInjected gas z_i: {comp.get('inj_gas')}"
        )
        st.session_state[basis_key] = basis_txt
        st.session_state[update_basis_key] = False
        st.success("Basis updated.")

    st.subheader("Inputs & Assumptions (editable)")
    st.text_area("Process Basis (auto-filled by clicking the button below)", key=basis_key)
    st.text_area("Options Considered / Trade Study", key=f"eng_trade_{stage}")
    st.text_area("Package Summary (one-pager)", key=f"eng_summary_{stage}")

    if st.button("Use Subsurface data in Basis"):
        st.session_state[update_basis_key] = True
        st.rerun()

# -------------------- Finalize & save artifacts --------------------
    if st.button("Finalize Engineering Package"):
        _mark_deliverable(stage, deliverable, "Done")
        _set_artifact_status(artifact, "Approved")

        # Only the stage package is saved here.
        pkg = {
            "basis":   st.session_state.get(f"eng_basis_{stage}", ""),
            "trade":   st.session_state.get(f"eng_trade_{stage}", ""),
            "summary": st.session_state.get(f"eng_summary_{stage}", ""),
            "design_point": {"oil_stbpd": oil_dp, "gas_scfpd": gas_dp, "water_bwpd": wat_dp},
        }
        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")
        save_artifact(project_id, phase_id, "Engineering", artifact, pkg, status="Approved")

        st.success(f"{deliverable} finalized. Note: Equipment_List / Utilities / PFD are authored by the Simulator.")
