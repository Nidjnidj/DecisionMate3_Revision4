# workflows/pm_mfg/capex_opex_estimator.py
from __future__ import annotations
import streamlit as st
import pandas as pd
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

# ---- helpers ----
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
        st.session_state.pop("active_view", None); st.session_state.pop("module_info", None); st.experimental_rerun()

def _seed():
    if "capex_df" not in st.session_state:
        st.session_state.capex_df = pd.DataFrame([
            {"Category":"Equipment","Item":"Body shop line","Cost (MUSD)":350.0},
            {"Category":"Building","Item":"Plant building & fit-out","Cost (MUSD)":420.0},
            {"Category":"Utilities","Item":"Power substation","Cost (MUSD)":60.0},
        ])
    if "opex_df" not in st.session_state:
        st.session_state.opex_df = pd.DataFrame([
            {"Category":"Labor","Yearly Cost (MUSD)":140.0},
            {"Category":"Energy","Yearly Cost (MUSD)":40.0},
            {"Category":"Maintenance","Yearly Cost (MUSD)":25.0},
        ])

def run():
    st.title("💰 CAPEX/OPEX Estimator — Placeholder")
    # Prefill hook from PM Hub (optional)
    pf = st.session_state.pop("prefill_cost", None)
    if pf:
        # Example: add a default row if empty, scaled by area/lines
        lines = int(pf.get("lines_required", 1) or 1)
        area  = float(pf.get("est_area_m2", 0) or 0.0)
        if "capex_df" in st.session_state and st.session_state.capex_df.empty:
            st.session_state.capex_df = pd.DataFrame([
                {"Category":"Equipment","Item":"Production lines","Cost (MUSD)": max(50.0, 30.0*lines)},
                {"Category":"Building","Item":"Plant building & fit-out","Cost (MUSD)": max(40.0, 0.0004*area)},
            ])

    st.caption("Quick parametric roll-up; saves Finance/Cost_Model for FEED.")

    _seed()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("CAPEX")
        capex = st.data_editor(
            st.session_state.capex_df, key="capex_editor",
            num_rows="dynamic", use_container_width=True,
            column_config={"Cost (MUSD)": st.column_config.NumberColumn(min_value=0.0, step=1.0)}
        )
        st.session_state.capex_df = capex
    with col2:
        st.subheader("OPEX (Annual)")
        opex = st.data_editor(
            st.session_state.opex_df, key="opex_editor",
            num_rows="dynamic", use_container_width=True,
            column_config={"Yearly Cost (MUSD)": st.column_config.NumberColumn(min_value=0.0, step=1.0)}
        )
        st.session_state.opex_df = opex

    capex_tot = float(pd.to_numeric(capex["Cost (MUSD)"], errors="coerce").fillna(0).sum())
    opex_tot = float(pd.to_numeric(opex["Yearly Cost (MUSD)"], errors="coerce").fillna(0).sum())
    k1, k2 = st.columns(2)
    k1.metric("CAPEX total (MUSD)", f"{capex_tot:,.1f}")
    k2.metric("OPEX total / yr (MUSD)", f"{opex_tot:,.1f}")

    pid, phid = _ids()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Cost_Model (Draft)", key="cost_save"):
            rec = save_artifact(pid, phid, "Finance", "Cost_Model",
                                {"capex": capex.to_dict("records"), "opex": opex.to_dict("records"),
                                 "totals":{"capex_musd":capex_tot,"opex_musd":opex_tot}},
                                status="Draft")
            st.success(f"Cost_Model saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve Cost_Model", key="cost_approve"):
            rec = save_artifact(pid, phid, "Finance", "Cost_Model",
                                {"capex": capex.to_dict("records"), "opex": opex.to_dict("records"),
                                 "totals":{"capex_musd":capex_tot,"opex_musd":opex_tot}},
                                status="Pending")
            approve_artifact(pid, rec.get("artifact_id")); st.success("Cost_Model Approved.")

    if st.button("↩ Back to PM Hub", key="cost_back"):
        back_to_hub()
