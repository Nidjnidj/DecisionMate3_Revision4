# workflows/pm_arch_construction/concept_kit.py
from __future__ import annotations
import math, re
from datetime import datetime
from typing import Any, Dict

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE   = "Concept_Massing"
WORKSTREAM = "Design"

# ---------- helpers ----------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _number(label: str, default: float, key: str, minv: float = 0.0, step: float = 1.0) -> float:
    return float(st.number_input(label, min_value=minv, value=default, step=step, key=key))

# ---------- main ----------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Concept Design Kit (Massing)")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    latest = get_latest(pid, ART_TYPE, phid)
    init = latest.get("data", {}) if latest else {}

    with st.expander("Context", expanded=True):
        mode = st.radio(
            "Concept type",
            ["Building / Campus", "Industrial"],
            index=0 if (init.get("mode") in [None, "building"]) else 1,
            key=_keyify("ck_mode", pid, phid),
        )

    if mode == "Building / Campus":
        st.markdown("#### Building / Campus Parameters")

        c1, c2, c3 = st.columns(3)
        with c1:
            site_area = _number("Site area (m²)", init.get("site_area", 20_000.0), _keyify("ck_site", pid, phid), step=100.0)
            coverage  = _number("Max building coverage (0–1.0)", init.get("coverage", 0.45), _keyify("ck_cov", pid, phid), 0.0, 0.01)
            far_max   = _number("Max FAR", init.get("far_max", 3.0), _keyify("ck_far", pid, phid), 0.0, 0.1)
        with c2:
            f2f       = _number("Floor-to-floor height (m)", init.get("f2f", 3.5), _keyify("ck_f2f", pid, phid), 2.8, 0.1)
            eff       = _number("Net-to-gross efficiency (0–1.0)", init.get("eff", 0.82), _keyify("ck_eff", pid, phid), 0.5, 0.01)
            target_gfa= _number("Target GFA (m²) (optional)", init.get("target_gfa", 0.0), _keyify("ck_tgfa", pid, phid), 0.0, 100.0)
        with c3:
            sp_per_100m2 = _number("Parking ratio (spaces / 100 m² net)", init.get("ratio_per_100m2", 2.0), _keyify("ck_ratio", pid, phid), 0.0, 0.1)
            space_m2     = _number("Area per space incl. aisles (m²)", init.get("space_m2", 30.0), _keyify("ck_space_m2", pid, phid), 10.0, 1.0)

        footprint = site_area * coverage
        gfa_cap   = site_area * far_max
        gfa       = max(target_gfa, gfa_cap) if target_gfa else gfa_cap
        floors    = max(1, math.ceil(gfa / max(1.0, footprint)))
        height    = floors * f2f

        net_area  = gfa * eff
        core_area = gfa - net_area

        # parking estimate (quick rule-of-thumb)
        req_spaces = (net_area / 100.0) * sp_per_100m2
        surf_cap   = (site_area - footprint) / max(1.0, space_m2)  # very rough
        needs_struct = req_spaces > max(0.0, surf_cap)

        st.markdown("#### Results")
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Footprint (m²)", f"{footprint:,.0f}")
        with m2: st.metric("Floors", floors)
        with m3: st.metric("GFA (m²)", f"{gfa:,.0f}")
        with m4: st.metric("Height (m)", f"{height:,.1f}")

        m5, m6, m7, m8 = st.columns(4)
        with m5: st.metric("Net usable (m²)", f"{net_area:,.0f}")
        with m6: st.metric("Core/services (m²)", f"{core_area:,.0f}")
        with m7: st.metric("Parking required (spaces)", f"{req_spaces:,.0f}")
        with m8: st.metric("Surface capacity (spaces)", f"{surf_cap:,.0f}")

        if needs_struct:
            st.warning("Estimated parking exceeds surface capacity — structured parking may be required.")

        payload: Dict[str, Any] = {
            "mode": "building",
            "site_area": site_area,
            "coverage": coverage,
            "far_max": far_max,
            "f2f": f2f,
            "eff": eff,
            "target_gfa": target_gfa,
            "results": {
                "footprint_m2": footprint,
                "floors": floors,
                "gfa_m2": gfa,
                "height_m": height,
                "net_m2": net_area,
                "core_m2": core_area,
                "parking": {
                    "ratio_per_100m2": sp_per_100m2,
                    "space_m2": space_m2,
                    "required_spaces": req_spaces,
                    "surface_capacity": surf_cap,
                    "structured_needed": bool(needs_struct),
                },
            },
            "ts": datetime.utcnow().isoformat() + "Z",
        }

    else:
        st.markdown("#### Industrial Parameters")
        c1, c2, c3 = st.columns(3)
        with c1:
            plot_area = _number("Plot area (m²)", init.get("plot_area", 50_000.0), _keyify("ik_plot", pid, phid), step=100.0)
            coverage  = _number("Building coverage (0–1.0)", init.get("i_coverage", 0.35), _keyify("ik_cov", pid, phid), 0.0, 0.01)
        with c2:
            eave_h    = _number("Eave height (m)", init.get("eave_h", 12.0), _keyify("ik_eave", pid, phid), 6.0, 0.5)
            bay_w     = _number("Typical bay width (m)", init.get("bay_w", 24.0), _keyify("ik_bay", pid, phid), 6.0, 0.5)
        with c3:
            pave_ratio= _number("Yard paving ratio (0–1.0)", init.get("pave_ratio", 0.25), _keyify("ik_pave", pid, phid), 0.0, 0.01)

        building_area = plot_area * coverage
        yard_area     = plot_area * pave_ratio

        st.markdown("#### Results")
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Building area (m²)", f"{building_area:,.0f}")
        with m2: st.metric("Yard paving (m²)", f"{yard_area:,.0f}")
        with m3: st.metric("Eave height (m)", f"{eave_h:,.1f}")

        payload = {
            "mode": "industrial",
            "plot_area": plot_area,
            "coverage": coverage,
            "eave_h": eave_h,
            "bay_w": bay_w,
            "pave_ratio": pave_ratio,
            "results": {
                "building_area_m2": building_area,
                "yard_area_m2": yard_area,
            },
            "ts": datetime.utcnow().isoformat() + "Z",
        }

    st.divider()
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Save Concept (Draft)", key=_keyify("ck_save_d", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
            st.success("Concept saved (Draft).")
    with b2:
        if st.button("Save Concept (Pending)", key=_keyify("ck_save_p", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            st.success("Concept saved (Pending).")
    with b3:
        if st.button("Save & Approve Concept", key=_keyify("ck_save_a", pid, phid)):
            rec = save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            try:
                from artifact_registry import approve_artifact
                approve_artifact(pid, rec.get("artifact_id"))
            except Exception:
                pass
            st.success("Concept saved and Approved.")
