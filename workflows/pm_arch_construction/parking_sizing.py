# workflows/pm_arch_construction/parking_sizing.py
from __future__ import annotations
import re
from datetime import datetime
from typing import Any, Dict

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE   = "Parking_Sizing"
WORKSTREAM = "Planning"

def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Parking Sizing")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    latest = get_latest(pid, ART_TYPE, phid)
    init = latest.get("data", {}) if latest else {}

    st.caption("Ratios are rule-of-thumb defaults. Adjust for your jurisdiction’s code.")

    # --- inputs / ratios ---
    c0, c00 = st.columns([1,1])
    with c0:
        # site capacity check
        site_area   = st.number_input("Site area (m²)", min_value=0.0, value=float(init.get("site_area", 20_000.0)), step=100.0, key=_keyify("pk_site", pid, phid))
        footprint   = st.number_input("Building footprint (m²)", min_value=0.0, value=float(init.get("footprint", 6_000.0)), step=100.0, key=_keyify("pk_fp", pid, phid))
        space_m2    = st.number_input("Area per parking space incl. aisles (m²)", min_value=10.0, value=float(init.get("space_m2", 30.0)), step=1.0, key=_keyify("pk_space_m2", pid, phid))
    with c00:
        occ_factor  = st.number_input("Occupancy factor (0–1.0)", min_value=0.1, max_value=1.0, value=float(init.get("occ_factor", 0.90)), step=0.05, key=_keyify("pk_occ", pid, phid))
        ada_pct     = st.number_input("Accessible (ADA) %", min_value=0.0, max_value=20.0, value=float(init.get("ada_pct", 2.0)), step=0.5, key=_keyify("pk_ada", pid, phid))
        ev_pct      = st.number_input("EV-ready %", min_value=0.0, max_value=50.0, value=float(init.get("ev_pct", 10.0)), step=1.0, key=_keyify("pk_ev", pid, phid))

    st.markdown("#### Land Use Mix")
    colA, colB, colC, colD, colE, colF = st.columns(6)

    # default areas / units
    with colA:
        office_gfa  = st.number_input("Office GFA (m²)", min_value=0.0, value=float(init.get("office_gfa", 25_000.0)), step=100.0, key=_keyify("pk_off", pid, phid))
        office_r    = st.number_input("Office ratio (spaces / 100 m² net)", min_value=0.0, value=float(init.get("office_ratio", 2.0)), step=0.1, key=_keyify("pk_offr", pid, phid))
    with colB:
        retail_gfa  = st.number_input("Retail GFA (m²)", min_value=0.0, value=float(init.get("retail_gfa", 5_000.0)), step=50.0, key=_keyify("pk_ret", pid, phid))
        retail_r    = st.number_input("Retail ratio (spaces / 100 m² net)", min_value=0.0, value=float(init.get("retail_ratio", 3.0)), step=0.1, key=_keyify("pk_retr", pid, phid))
    with colC:
        res_units   = st.number_input("Residential units (ea)", min_value=0, value=int(init.get("res_units", 200)), step=1, key=_keyify("pk_resu", pid, phid))
        res_r       = st.number_input("Residential ratio (spaces / unit)", min_value=0.0, value=float(init.get("res_ratio", 1.2)), step=0.1, key=_keyify("pk_resr", pid, phid))
    with colD:
        hotel_keys  = st.number_input("Hotel rooms (ea)", min_value=0, value=int(init.get("hotel_keys", 120)), step=1, key=_keyify("pk_hotel", pid, phid))
        hotel_r     = st.number_input("Hotel ratio (spaces / room)", min_value=0.0, value=float(init.get("hotel_ratio", 0.8)), step=0.1, key=_keyify("pk_hr", pid, phid))
    with colE:
        hosp_beds   = st.number_input("Hospital beds (ea)", min_value=0, value=int(init.get("hosp_beds", 0)), step=1, key=_keyify("pk_hosp", pid, phid))
        hosp_r      = st.number_input("Hospital ratio (spaces / bed)", min_value=0.0, value=float(init.get("hosp_ratio", 4.0)), step=0.1, key=_keyify("pk_hospr", pid, phid))
    with colF:
        other_basis = st.selectbox("Other basis", ["GFA (m²)", "Units"], index=0 if init.get("other_basis", "gfa") == "gfa" else 1, key=_keyify("pk_ob", pid, phid))
        other_qty   = st.number_input("Other quantity", min_value=0.0, value=float(init.get("other_qty", 0.0)), step=1.0, key=_keyify("pk_oq", pid, phid))
        other_ratio = st.number_input("Other ratio (per 100 m² or per unit)", min_value=0.0, value=float(init.get("other_ratio", 0.0)), step=0.1, key=_keyify("pk_or", pid, phid))

    # --- compute ---
    office_spaces = (office_gfa / 100.0) * office_r
    retail_spaces = (retail_gfa / 100.0) * retail_r
    res_spaces    = res_units * res_r
    hotel_spaces  = hotel_keys * hotel_r
    hosp_spaces   = hosp_beds * hosp_r
    other_spaces  = (other_qty / 100.0) * other_ratio if other_basis.startswith("GFA") else other_qty * other_ratio

    base_sum = sum([office_spaces, retail_spaces, res_spaces, hotel_spaces, hosp_spaces, other_spaces])
    adj_sum  = base_sum * occ_factor

    ada_spaces = max(1.0, adj_sum * (ada_pct / 100.0)) if adj_sum > 0 else 0.0
    ev_spaces  = max(0.0, adj_sum * (ev_pct / 100.0))
    total_req  = adj_sum + ada_spaces  # ADA added on top; many codes include it within the total—adjust as needed

    surface_capacity = max(0.0, (site_area - footprint) / max(1.0, space_m2))
    needs_struct = total_req > surface_capacity

    st.markdown("#### Results")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Base spaces (pre-occupancy)", f"{base_sum:,.0f}")
    with m2: st.metric("Adjusted by occupancy", f"{adj_sum:,.0f}")
    with m3: st.metric("ADA spaces", f"{ada_spaces:,.0f}")
    with m4: st.metric("EV-ready spaces", f"{ev_spaces:,.0f}")

    m5, m6 = st.columns(2)
    with m5: st.metric("Total required spaces", f"{total_req:,.0f}")
    with m6: st.metric("Surface capacity", f"{surface_capacity:,.0f}")

    if needs_struct:
        st.warning("Required spaces exceed estimated surface capacity — structured parking likely needed.")

    # --- payload & save ---
    payload: Dict[str, Any] = {
        "site_area": site_area,
        "footprint": footprint,
        "space_m2": space_m2,
        "occ_factor": occ_factor,
        "ada_pct": ada_pct,
        "ev_pct": ev_pct,
        "uses": {
            "office": {"gfa_m2": office_gfa, "ratio_per_100m2": office_r, "spaces": office_spaces},
            "retail": {"gfa_m2": retail_gfa, "ratio_per_100m2": retail_r, "spaces": retail_spaces},
            "residential": {"units": res_units, "ratio_per_unit": res_r, "spaces": res_spaces},
            "hotel": {"keys": hotel_keys, "ratio_per_key": hotel_r, "spaces": hotel_spaces},
            "hospital": {"beds": hosp_beds, "ratio_per_bed": hosp_r, "spaces": hosp_spaces},
            "other": {"basis": "gfa" if other_basis.startswith("GFA") else "units",
                      "qty": other_qty, "ratio": other_ratio, "spaces": other_spaces},
        },
        "summary": {
            "base_sum": base_sum,
            "adjusted_sum": adj_sum,
            "ada_spaces": ada_spaces,
            "ev_spaces": ev_spaces,
            "total_required": total_req,
            "surface_capacity": surface_capacity,
            "structured_needed": bool(needs_struct),
        },
        "ts": datetime.utcnow().isoformat() + "Z",
    }

    st.divider()
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Save Parking (Draft)", key=_keyify("pk_save_d", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
            st.success("Parking sizing saved (Draft).")
    with b2:
        if st.button("Save Parking (Pending)", key=_keyify("pk_save_p", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            st.success("Parking sizing saved (Pending).")
    with b3:
        if st.button("Save & Approve Parking", key=_keyify("pk_save_a", pid, phid)):
            rec = save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            try:
                from artifact_registry import approve_artifact
                approve_artifact(pid, rec.get("artifact_id"))
            except Exception:
                pass
            st.success("Parking sizing saved and Approved.")
