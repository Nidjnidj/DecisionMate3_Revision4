# workflows/pm_mfg/construction_plan.py
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
    if "cplan_milestones" not in st.session_state:
        st.session_state.cplan_milestones = pd.DataFrame([
            {"Milestone":"Groundbreaking","Date":"","Owner":"PMO"},
            {"Milestone":"Building Dry-in","Date":"","Owner":"CM"},
            {"Milestone":"Mechanical Completion","Date":"","Owner":"CM"},
            {"Milestone":"RFSU","Date":"","Owner":"PMO"},
        ])

def run():
    st.title("🏗️ Construction Plan — Placeholder")
    st.caption("Exec plan overview + milestones for Execution stage.")

    overview = st.text_area("Plan overview (phasing, access, interfaces, HSE)", height=160, key="cplan_overview")
    _seed()
    ms = st.data_editor(
        st.session_state.cplan_milestones, key="cplan_ms_editor",
        num_rows="dynamic", use_container_width=True,
        column_config={"Date": st.column_config.TextColumn(help="YYYY-MM-DD")}
    )
    st.session_state.cplan_milestones = ms

    pid, phid = _ids()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Construction_Plan (Draft)", key="cplan_save"):
            rec = save_artifact(pid, phid, "PMO", "Construction_Plan",
                                {"overview": overview, "milestones": ms.to_dict("records")},
                                status="Draft")
            st.success(f"Saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve Construction_Plan", key="cplan_approve"):
            rec = save_artifact(pid, phid, "PMO", "Construction_Plan",
                                {"overview": overview, "milestones": ms.to_dict("records")},
                                status="Pending")
            approve_artifact(pid, rec.get("artifact_id")); st.success("Construction_Plan Approved.")

    if st.button("↩ Back to PM Hub", key="cplan_back"):
        back_to_hub()
