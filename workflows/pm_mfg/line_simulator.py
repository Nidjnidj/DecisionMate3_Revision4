# workflows/pm_mfg/line_simulator.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import uuid

# ---- artifact registry (real or fallback) ----
def _ensure_fallback(): st.session_state.setdefault("_artifacts_store", {})
def _key(pid, phid): return f"{pid}::{phid}"
def _save_fallback(pid, phid, ws, t, data, status="Draft", sources=None):
    _ensure_fallback()
    rec = {"artifact_id": uuid.uuid4().hex, "project_id": pid, "phase_id": phid,
           "workstream": ws, "type": t, "data": data or {}, "status": status or "Draft",
           "sources": sources or []}
    st.session_state["_artifacts_store"].setdefault(_key(pid, phid), []).append(rec); return rec
def _approve_fallback(pid, aid):
    _ensure_fallback()
    for items in st.session_state["_artifacts_store"].values():
        for r in items:
            if r["artifact_id"] == aid and r["project_id"] == pid: r["status"] = "Approved"; return
try:
    from services.artifact_registry import save_artifact, approve_artifact  # type: ignore
except Exception:
    save_artifact, approve_artifact = _save_fallback, _approve_fallback  # type: ignore

def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    st.session_state["current_project_id"] = pid
    phid = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    st.session_state["current_phase_id"] = phid
    return pid, phid

def run():
    st.title("🧮 Line Simulator (serial line) — Placeholder")
    st.caption("Estimate line capacity, WIP, and lead time for concept and FEED decisions.")

    # Prefill from Footprint Sizer (optional)
    pf = st.session_state.pop("prefill_line_sim", None)
    default_stations = int(pf.get("stations_per_line", 20)) if pf else 20

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stations = st.number_input("Stations in serial line", min_value=1, value=default_stations, step=1)
    with c2:
        shifts = st.number_input("Shifts/day", min_value=1, max_value=4, value=2)
    with c3:
        workdays = st.number_input("Workdays/year", min_value=1, max_value=365, value=250)
    with c4:
        oee_pct = st.number_input("OEE (%)", min_value=1.0, max_value=100.0, value=85.0, step=0.5)

    # Station cycle times (sec)
    if "ls_ct" not in st.session_state:
        st.session_state.ls_ct = pd.DataFrame([{"Station": i+1, "CT (sec)": 60} for i in range(stations)])
    # keep size in sync
    if len(st.session_state.ls_ct) != stations:
        cur = st.session_state.ls_ct
        if len(cur) < stations:
            add = pd.DataFrame([{"Station": i+1, "CT (sec)": 60} for i in range(len(cur), stations)])
            st.session_state.ls_ct = pd.concat([cur, add], ignore_index=True)
        else:
            st.session_state.ls_ct = cur.iloc[:stations].reset_index(drop=True)

    st.subheader("Station cycle times (sec)")
    ct_df = st.data_editor(
        st.session_state.ls_ct, key="ls_ct_editor", num_rows="dynamic", use_container_width=True,
        column_config={"CT (sec)": st.column_config.NumberColumn(min_value=1, step=1)}
    )
    st.session_state.ls_ct = ct_df

    # Computations
    ct = pd.to_numeric(ct_df["CT (sec)"], errors="coerce").fillna(0).to_numpy()
    bottleneck_ct = float(ct.max()) if len(ct) else 0.0
    eff_ct = bottleneck_ct / (oee_pct / 100.0)
    seconds_per_year = workdays * shifts * 8 * 3600
    capacity_units_year = seconds_per_year / eff_ct if eff_ct > 0 else 0
    line_rate_uph = 3600.0 / eff_ct if eff_ct > 0 else 0
    lead_time_sec = float(ct.sum())  # serial sum (theoretical, no buffers)
    wip_theoretical = stations  # 1 unit per station as a base assumption

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Bottleneck CT (sec)", f"{bottleneck_ct:.0f}")
    k2.metric("Effective CT (sec)", f"{eff_ct:.0f}")
    k3.metric("Line rate (UPH)", f"{line_rate_uph:.1f}")
    k4.metric("Capacity (units/yr)", f"{int(capacity_units_year):,}")
    k5.metric("Theoretical WIP / Lead time", f"{int(wip_theoretical)} / {int(lead_time_sec)}s")

    # Scenario what-ifs
    st.subheader("What-if scenarios")
    if "ls_scen" not in st.session_state:
        st.session_state.ls_scen = pd.DataFrame([
            {"Scenario":"Base","OEE (%)":oee_pct,"Shifts":shifts,"Workdays":workdays,"Bottleneck CT (sec)":bottleneck_ct},
            {"Scenario":"Improve OEE","OEE (%)":min(95.0,oee_pct+5),"Shifts":shifts,"Workdays":workdays,"Bottleneck CT (sec)":bottleneck_ct},
            {"Scenario":"Add a shift","OEE (%)":oee_pct,"Shifts":min(4,shifts+1),"Workdays":workdays,"Bottleneck CT (sec)":bottleneck_ct},
        ])
    scen = st.data_editor(
        st.session_state.ls_scen, key="ls_scen_editor", num_rows="dynamic", use_container_width=True,
        column_config={"OEE (%)": st.column_config.NumberColumn(min_value=1.0, max_value=100.0, step=0.5),
                       "Shifts": st.column_config.NumberColumn(min_value=1, max_value=4, step=1),
                       "Workdays": st.column_config.NumberColumn(min_value=1, max_value=365, step=1),
                       "Bottleneck CT (sec)": st.column_config.NumberColumn(min_value=1, step=1)}
    )
    st.session_state.ls_scen = scen

    out_rows = []
    for _, r in scen.iterrows():
        eff_ct_i = float(r["Bottleneck CT (sec)"]) / (float(r["OEE (%)"]) / 100.0)
        sec_year_i = float(r["Workdays"]) * float(r["Shifts"]) * 8 * 3600
        cap_i = sec_year_i / eff_ct_i if eff_ct_i > 0 else 0
        uph_i = 3600.0 / eff_ct_i if eff_ct_i > 0 else 0
        out_rows.append({"Scenario": r["Scenario"], "UPH": uph_i, "Units/yr": cap_i})
    out_df = pd.DataFrame(out_rows)
    st.dataframe(out_df, use_container_width=True)

    pid, phid = _ids()
    c1, c2 = st.columns(2)
    payload = {
        "stations": int(stations), "ct_sec": ct_df.to_dict("records"),
        "oee_pct": float(oee_pct), "shifts": int(shifts), "workdays": int(workdays),
        "bottleneck_ct_sec": float(bottleneck_ct), "effective_ct_sec": float(eff_ct),
        "line_rate_uph": float(line_rate_uph), "capacity_units_year": float(capacity_units_year),
        "scenarios": scen.to_dict("records"), "scenario_results": out_df.to_dict("records"),
    }
    with c1:
        if st.button("💾 Save Line_Simulation (Draft)"):
            rec = save_artifact(pid, phid, "Engineering", "Line_Simulation", payload, status="Draft")
            st.success(f"Saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve Line_Simulation"):
            rec = save_artifact(pid, phid, "Engineering", "Line_Simulation", payload, status="Pending")
            approve_artifact(pid, rec.get("artifact_id")); st.success("Line_Simulation Approved.")
