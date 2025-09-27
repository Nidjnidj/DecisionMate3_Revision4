from __future__ import annotations
import uuid, streamlit as st

def _ensure_store(): st.session_state.setdefault("_artifacts_store", {})
def _key(pid, ph): return f"{pid}::{ph}"
def _save(pid, ph, ws, typ, data, status="Draft"):
    _ensure_store()
    rec = {"artifact_id": uuid.uuid4().hex, "project_id": pid, "phase_id": ph,
           "workstream": ws, "type": typ, "data": data or {}, "status": status}
    st.session_state["_artifacts_store"].setdefault(_key(pid,ph), []).append(rec); return rec
try:
    from services.artifact_registry import save_artifact as _svc  # type: ignore
    def _save(pid, ph, ws, typ, data, status="Draft"): return _svc(pid, ph, ws, typ, data, status)
except Exception:
    pass

def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    ph  = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    return pid, ph

def run():
    st.title("Engineering Program Brief")
    st.caption("High-level scope, processes, utilities and constraints to support the business case.")
    pid, ph = _ids()

    scope = st.text_area("Scope (process list, expected throughput, takt, etc.)", "")
    utilities = st.text_area("Utilities (power, water, air, waste)", "")
    constraints = st.text_area("Constraints & assumptions", "")
    if st.button("💾 Save Program Brief"):
        _save(pid, ph, "Engineering", "Program_Brief", {
            "scope": scope, "utilities": utilities, "constraints": constraints
        }, status="Draft")
        st.success("Saved Engineering / Program_Brief (Draft).")
