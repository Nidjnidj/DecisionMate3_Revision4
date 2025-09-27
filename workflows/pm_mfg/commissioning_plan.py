# workflows/pm_mfg/commissioning_plan.py
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
    if "comm_df" not in st.session_state:
        st.session_state.comm_df = pd.DataFrame([
            {"System":"Press Line A","Test":"Dry run","Owner":"Eng","Start":"","Finish":"","Status":"Planned"},
            {"System":"Paint Booth","Test":"Airflow balance","Owner":"MEP","Start":"","Finish":"","Status":"Planned"},
            {"System":"Assembly","Test":"Rate to takt","Owner":"Ops","Start":"","Finish":"","Status":"Planned"},
        ])

def run():
    st.title("🧪 Commissioning Plan — Placeholder")
    st.caption("Systems, tests, dates, and status for Execution/Start-up stage.")

    _seed()
    status_opts = ["Planned","In Progress","Hold","Passed","Failed"]

    df = st.data_editor(
        st.session_state.comm_df, key="comm_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "System": st.column_config.TextColumn(),
            "Test": st.column_config.TextColumn(),
            "Owner": st.column_config.TextColumn(),
            "Start": st.column_config.TextColumn(help="YYYY-MM-DD"),
            "Finish": st.column_config.TextColumn(help="YYYY-MM-DD"),
            "Status": st.column_config.SelectboxColumn(options=status_opts),
        }
    )
    st.session_state.comm_df = df

    pid, phid = _ids()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Commissioning_Plan (Draft)", key="comm_save"):
            rec = save_artifact(pid, phid, "PMO", "Commissioning_Plan",
                                {"systems": df.to_dict("records")}, status="Draft")
            st.success(f"Saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve Commissioning_Plan", key="comm_approve"):
            rec = save_artifact(pid, phid, "PMO", "Commissioning_Plan",
                                {"systems": df.to_dict("records")}, status="Pending")
            approve_artifact(pid, rec.get("artifact_id")); st.success("Commissioning_Plan Approved.")

    if st.button("↩ Back to PM Hub", key="comm_back"):
        back_to_hub()
