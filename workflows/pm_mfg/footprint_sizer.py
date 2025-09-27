# workflows/pm_mfg/footprint_sizer.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import uuid
import importlib
from math import ceil

# ============ artifact registry (real or fallback) ============
def _ensure_fallback(): st.session_state.setdefault("_artifacts_store", {})
def _key(pid, phid): return f"{pid}::{phid}"

def _save_fallback(pid, phid, ws, t, data, status="Draft", sources=None):
    _ensure_fallback()
    rec = {
        "artifact_id": uuid.uuid4().hex, "project_id": pid, "phase_id": phid,
        "workstream": ws, "type": t, "data": data or {}, "status": status or "Draft",
        "sources": sources or [],
    }
    st.session_state["_artifacts_store"].setdefault(_key(pid, phid), []).append(rec)
    return rec

def _approve_fallback(pid, aid):
    _ensure_fallback()
    for items in st.session_state["_artifacts_store"].values():
        for r in items:
            if r.get("artifact_id") == aid and r.get("project_id") == pid:
                r["status"] = "Approved"; return

try:
    from services.artifact_registry import save_artifact, approve_artifact  # type: ignore
except Exception:
    save_artifact, approve_artifact = _save_fallback, _approve_fallback  # type: ignore

# ============ helpers ============
def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    st.session_state["current_project_id"] = pid
    phid = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    st.session_state["current_phase_id"] = phid
    return pid, phid

try:
    from services.utils import back_to_hub
except Exception:
    def back_to_hub():
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

def _prefill_from_session():
    """Consume PM Hub prefill (if any) and seed sensible defaults."""
    pf = st.session_state.pop("prefill_footprint", None)
    if not pf:
        return
    # optional keys: annual_demand_units, workdays, shifts, ramp_months
    if "annual_demand_units" in pf and isinstance(pf["annual_demand_units"], (int, float)):
        st.session_state.setdefault("fs_demand_units", int(pf["annual_demand_units"]))
    if "workdays" in pf and isinstance(pf["workdays"], (int, float)):
        st.session_state.setdefault("fs_workdays", int(pf["workdays"]))
    if "shifts" in pf and isinstance(pf["shifts"], (int, float)):
        st.session_state.setdefault("fs_shifts", int(pf["shifts"]))
    if "ramp_months" in pf and isinstance(pf["ramp_months"], (int, float)):
        st.session_state.setdefault("fs_ramp", int(pf["ramp_months"]))

def _num(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return float(default)

# ============ UI ============
def run():
    st.title("📏 Footprint & Layout Sizer — Placeholder")
    st.caption("Estimate lines, stations, and building/site area. Saves an Engineering/Factory_Sizing artifact.")

    _prefill_from_session()

    # -------- Top context (basic program) --------
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        demand_units = st.number_input(
            "Annual demand (units/yr)", min_value=0, step=1000,
            value=int(st.session_state.get("fs_demand_units", 100000)),
            key="fs_demand_units_in",
        )
    with c2:
        shifts = st.number_input(
            "Shifts/day", min_value=1, max_value=4,
            value=int(st.session_state.get("fs_shifts", 2)),
            key="fs_shifts_in",
        )
    with c3:
        workdays = st.number_input(
            "Workdays/year", min_value=1, max_value=365,
            value=int(st.session_state.get("fs_workdays", 250)),
            key="fs_workdays_in",
        )
    with c4:
        oee_pct = st.number_input("OEE (%)", min_value=1.0, max_value=100.0, value=85.0, step=0.5, key="fs_oee")
    with c5:
        takt_sec_hint = st.number_input("Design bottleneck CT (sec)", min_value=1, value=60, step=1, key="fs_ct")

    # -------- Line structure assumptions --------
    c6, c7, c8, c9 = st.columns(4)
    with c6:
        stations_per_line = st.number_input("Stations per line", min_value=1, value=20, step=1, key="fs_stations")
    with c7:
        station_pitch_m = st.number_input("Station pitch (m)", min_value=1.0, value=3.0, step=0.5, key="fs_pitch")
    with c8:
        line_width_m = st.number_input("Line width (m)", min_value=2.0, value=6.0, step=0.5, key="fs_width")
    with c9:
        area_support_factor = st.number_input("Support area factor (× line area)", min_value=0.0, value=0.8, step=0.1, key="fs_supfac")

    # -------- Site assumptions --------
    c10, c11 = st.columns(2)
    with c10:
        gfa_to_site_coverage = st.number_input("Site coverage (building / site)", min_value=0.05, max_value=0.95, value=0.45, step=0.05, key="fs_cov")
    with c11:
        circulation_factor = st.number_input("Circulation/buffers factor", min_value=1.0, value=1.30, step=0.05, key="fs_circ")

    # -------- Calculations --------
    # effective cycle time at bottleneck considering OEE
    eff_ct_sec = takt_sec_hint / (oee_pct / 100.0)
    # per-line annual capacity
    seconds_year = workdays * shifts * 8 * 3600
    per_line_annual = seconds_year / eff_ct_sec if eff_ct_sec > 0 else 0
    lines_required = int(ceil((demand_units / per_line_annual) if per_line_annual else 0))
    lines_required = max(1, lines_required)

    # physical footprint
    line_length_m = stations_per_line * station_pitch_m
    single_line_area = line_length_m * line_width_m
    single_line_area_eff = single_line_area * circulation_factor
    total_line_area = single_line_area_eff * lines_required
    support_area = total_line_area * area_support_factor
    building_gfa_m2 = total_line_area + support_area
    site_area_m2 = building_gfa_m2 / max(1e-6, gfa_to_site_coverage)
    site_acres = site_area_m2 / 4046.8564224

    # show KPIs
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Per-line capacity (units/yr)", f"{int(per_line_annual):,}")
    k2.metric("Lines required", lines_required)
    k3.metric("Line length (m)", f"{line_length_m:,.1f}")
    k4.metric("Line area/line (m²)", f"{single_line_area_eff:,.0f}")
    k5.metric("Building GFA (m²)", f"{building_gfa_m2:,.0f}")
    k6.metric("Site (acres)", f"{site_acres:,.1f}")

    st.divider()

    # optional: station groups editor (rough mix; not essential for placeholder)
    st.subheader("(Optional) Station groups")
    if "fs_groups" not in st.session_state:
        st.session_state.fs_groups = pd.DataFrame([
            {"Group":"Load/Unload","Stations":2},
            {"Group":"Process","Stations":stations_per_line-4 if stations_per_line>=4 else max(0, stations_per_line-2)},
            {"Group":"Inspection","Stations":2},
        ])
    groups = st.data_editor(
        st.session_state.fs_groups, key="fs_groups_editor",
        num_rows="dynamic", use_container_width=True,
        column_config={
            "Group": st.column_config.TextColumn(),
            "Stations": st.column_config.NumberColumn(min_value=0, step=1),
        }
    )
    st.session_state.fs_groups = groups

    # -------- Save / Approve / Navigate --------
    pid, phid = _ids()
    payload = {
        "inputs": {
            "annual_demand_units": int(demand_units),
            "shifts": int(shifts),
            "workdays": int(workdays),
            "oee_pct": float(oee_pct),
            "design_bottleneck_ct_sec": int(takt_sec_hint),
            "stations_per_line": int(stations_per_line),
            "station_pitch_m": float(station_pitch_m),
            "line_width_m": float(line_width_m),
            "circulation_factor": float(circulation_factor),
            "support_area_factor": float(area_support_factor),
            "site_coverage": float(gfa_to_site_coverage),
        },
        "derived": {
            "effective_ct_sec": float(eff_ct_sec),
            "per_line_annual_capacity": float(per_line_annual),
            "lines_required": int(lines_required),
            "line_length_m": float(line_length_m),
            "single_line_area_m2": float(single_line_area),
            "single_line_area_eff_m2": float(single_line_area_eff),
            "total_line_area_m2": float(total_line_area),
            "support_area_m2": float(support_area),
            "building_gfa_m2": float(building_gfa_m2),
            "site_area_m2": float(site_area_m2),
            "site_acres": float(site_acres),
        },
        "station_groups": groups.to_dict("records"),
    }

    cA, cB, cC, cD = st.columns(4)
    with cA:
        if st.button("💾 Save Factory_Sizing (Draft)", key="fs_save"):
            rec = save_artifact(pid, phid, "Engineering", "Factory_Sizing", payload, status="Draft")
            st.success(f"Saved (id: {rec.get('artifact_id','')[:8]}…).")
    with cB:
        if st.button("✅ Approve Factory_Sizing", key="fs_approve"):
            rec = save_artifact(pid, phid, "Engineering", "Factory_Sizing", payload, status="Pending")
            approve_artifact(pid, rec.get("artifact_id"))
            st.success("Factory_Sizing Approved.")
    with cC:
        if st.button("➡️ Open Line Simulator", key="fs_to_line_sim"):
            # pass stations_per_line to the Line Simulator
            st.session_state["prefill_line_sim"] = {"stations_per_line": int(stations_per_line)}
            try:
                mod = importlib.import_module("workflows.pm_mfg.line_simulator")
                mod.run()
            except Exception as e:
                st.warning(f"Could not open line simulator in-place: {e}. Open it from PM Hub instead.")
    with cD:
        if st.button("↩ Back to PM Hub", key="fs_back"):
            back_to_hub()

    st.caption("Note: CAPEX/OPEX Estimator and Schedule Developer read this sizing via PM Hub prefills.")
