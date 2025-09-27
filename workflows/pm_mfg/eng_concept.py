# workflows/pm_mfg/eng_concept.py
from __future__ import annotations
import streamlit as st
import uuid

# ---- artifact registry (real or fallback) ----
def _ensure_fallback():
    st.session_state.setdefault("_artifacts_store", {})
def _key(pid, phid): return f"{pid}::{phid}"
def _save_fallback(pid, phid, ws, t, data, status="Draft", sources=None):
    _ensure_fallback()
    rec = {
        "artifact_id": uuid.uuid4().hex, "project_id": pid, "phase_id": phid,
        "workstream": ws, "type": t, "data": data or {}, "status": status or "Draft",
        "sources": sources or [],
    }
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
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

# ---- UI ----
def run():
    st.title("📐 Engineering Concept (notes)")
    st.caption("Light placeholder to capture concept layout/utility basis in Pre-FEED.")

    layout = st.text_area("Layout concept (key flows, lines, docks, storage)", height=160, key="engc_layout")
    utilities = st.text_area("Utilities/MEP basis (power, air, water, HVAC)", height=140, key="engc_utils")
    risks = st.text_area("Key risks/assumptions", height=120, key="engc_risks")

    pid, phid = _ids()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💾 Save as Draft", key="engc_save"):
            rec = save_artifact(pid, phid, "Engineering", "Layout_Concept",
                                {"layout": layout, "utilities": utilities, "risks": risks},
                                status="Draft")
            st.success(f"Saved Draft (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Save & Approve", key="engc_approve"):
            rec = save_artifact(pid, phid, "Engineering", "Layout_Concept",
                                {"layout": layout, "utilities": utilities, "risks": risks},
                                status="Pending")
            approve_artifact(pid, rec.get("artifact_id"))
            st.success("Layout_Concept Approved.")
    with c3:
        if st.button("↩ Back to PM Hub", key="engc_back"):
            back_to_hub()
