# workflows/pm_mfg/schedule_developer_mfg.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import uuid

# ---- artifact registry (real or fallback) ----
def _ensure_fallback():
    st.session_state.setdefault("_artifacts_store", {})
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

def _seed_defaults():
    if "sched_wbs" not in st.session_state:
        st.session_state.sched_wbs = pd.DataFrame([
            {"id":"1","parent":"","name":"Factory Project","type":"Project","owner":"PM"},
            {"id":"1.1","parent":"1","name":"Concept Layout & Utilities","type":"WP","owner":"Eng"},
            {"id":"1.2","parent":"1","name":"Long-Lead Equipment","type":"WP","owner":"Proc"},
            {"id":"1.3","parent":"1","name":"Building & Fit-out","type":"WP","owner":"CM"},
            {"id":"1.4","parent":"1","name":"Line Install & Commissioning","type":"WP","owner":"Eng"},
        ])
    if "sched_acts" not in st.session_state:
        st.session_state.sched_acts = pd.DataFrame([
            {"id":"A1","name":"Freeze Concept Layout","wbs_id":"1.1","dur_days":20,"predecessors":""},
            {"id":"A2","name":"Order Long-Lead","wbs_id":"1.2","dur_days":30,"predecessors":"A1"},
            {"id":"A3","name":"Building & Fit-out","wbs_id":"1.3","dur_days":60,"predecessors":"A1"},
            {"id":"A4","name":"Install Lines","wbs_id":"1.4","dur_days":30,"predecessors":"A2,A3"},
            {"id":"A5","name":"Commissioning","wbs_id":"1.4","dur_days":25,"predecessors":"A4"},
        ])

def run():
    st.title("📆 Schedule Developer (L2/L3) — Placeholder")
    st.caption("Edit WBS and activities. Save WBS & Schedule_Network artifacts for FEED.")

    _seed_defaults()

    st.subheader("WBS")
    wbs = st.data_editor(
        st.session_state.sched_wbs, key="sched_wbs_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn(help="e.g., 1.2.3"),
            "parent": st.column_config.TextColumn(help="parent id"),
            "name": st.column_config.TextColumn(),
            "type": st.column_config.SelectboxColumn(options=["Project","WP","Task"]),
            "owner": st.column_config.TextColumn(),
        },
    )
    st.session_state.sched_wbs = wbs

    st.subheader("Activities")
    acts = st.data_editor(
        st.session_state.sched_acts, key="sched_acts_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn(),
            "name": st.column_config.TextColumn(),
            "wbs_id": st.column_config.TextColumn(),
            "dur_days": st.column_config.NumberColumn(min_value=1, step=1),
            "predecessors": st.column_config.TextColumn(help="comma-separated IDs, e.g., A1,A2"),
        },
    )
    st.session_state.sched_acts = acts

    pid, phid = _ids()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("💾 Save WBS (Draft)", key="sched_save_wbs"):
            rec = save_artifact(pid, phid, "Schedule", "WBS", {"nodes": wbs.to_dict("records")}, status="Draft")
            st.success(f"WBS saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve WBS", key="sched_approve_wbs"):
            rec = save_artifact(pid, phid, "Schedule", "WBS", {"nodes": wbs.to_dict("records")}, status="Pending")
            approve_artifact(pid, rec.get("artifact_id")); st.success("WBS Approved.")
    with c3:
        if st.button("💾 Save Network (Draft)", key="sched_save_net"):
            # split predecessor strings into lists
            a = acts.copy()
            a["pred_list"] = a["predecessors"].apply(lambda s: [x.strip() for x in str(s).split(",") if x.strip()])
            payload = {"activities": a.drop(columns=["predecessors"]).to_dict("records")}
            rec = save_artifact(pid, phid, "Schedule", "Schedule_Network", payload, status="Draft", sources=["WBS"])
            st.success(f"Schedule_Network saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c4:
        if st.button("✅ Approve Network", key="sched_approve_net"):
            a = acts.copy()
            a["pred_list"] = a["predecessors"].apply(lambda s: [x.strip() for x in str(s).split(",") if x.strip()])
            payload = {"activities": a.drop(columns=["predecessors"]).to_dict("records")}
            rec = save_artifact(pid, phid, "Schedule", "Schedule_Network", payload, status="Pending", sources=["WBS"])
            approve_artifact(pid, rec.get("artifact_id")); st.success("Schedule_Network Approved.")

    if st.button("↩ Back to PM Hub", key="sched_back"):
        back_to_hub()
