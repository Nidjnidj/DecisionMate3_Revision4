# utils/artifact_bridge.py  (place at repo root as artifact_bridge.py)
from __future__ import annotations
import time
from typing import Any, Dict, Optional

# Try real backend first
_HAS_BACKEND = False
try:
    from artifact_registry import (
        save_artifact as _save_artifact,
        get_latest as _get_latest,
        approve_artifact as _approve_artifact,
        list_required_artifacts as _list_required_artifacts,
    )
    _HAS_BACKEND = True
except Exception:
    _HAS_BACKEND = False

# Optional: Streamlit session store for fallback
try:
    import streamlit as st
except Exception:
    st = None

def _ss():
    if st is None:
        raise RuntimeError("Streamlit not available for fallback store.")
    if "ARTF_STORE" not in st.session_state:
        st.session_state.ARTF_STORE = {}
    return st.session_state.ARTF_STORE

def _current_ids(project_id: Optional[str] = None) -> tuple[str, str]:
    pid = project_id or (st.session_state.get("active_project_id")
                         or st.session_state.get("current_project_id")
                         or "P-DEMO")
    phid = (st.session_state.get("current_phase_id")
            or f"PH-{st.session_state.get('fel_stage', 'FEL1')}")
    return str(pid), str(phid)

# Simple mapping to a workstream label per IT stage/type
_WORKSTREAM_BY_STAGE = {
    "BusinessCase": "PMO",
    "Engineering":  "Architecture",
    "Schedule":     "Delivery",
    "Cost":         "Finance",
}

def _workstream_for(stage_or_type: Optional[str]) -> str:
    if not stage_or_type:
        return "PMO"
    return _WORKSTREAM_BY_STAGE.get(stage_or_type, "PMO")

# ---------------- Public API (used by IT modules) ----------------

def save_artifact(project_id: str, artifact_type: str, data: Dict[str, Any],
                  stage: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Save an artifact and return a normalized record with 'approved' boolean.
    """
    if _HAS_BACKEND:
        pid, phid = _current_ids(project_id)
        workstream = _workstream_for(stage or artifact_type)
        rec = _save_artifact(
            pid, phid, workstream, artifact_type, data,
            status="Draft", tags=[stage] if stage else None
        )
        return {
            "id": rec["artifact_id"],
            "ts": rec.get("updated_at", int(time.time())),
            "project_id": pid,
            "artifact_type": rec["type"],
            "data": rec.get("data", {}),
            "approved": str(rec.get("status", "")).lower() == "approved",
            "stage": stage,
            "meta": meta or {},
        }

    # Fallback (in-session)
    store = _ss()
    key = (project_id, artifact_type)
    record = {
        "id": f"{artifact_type}-{int(time.time())}",
        "ts": int(time.time()),
        "project_id": project_id,
        "artifact_type": artifact_type,
        "stage": stage,
        "meta": meta or {},
        "data": data,
        "approved": False,
    }
    store.setdefault(key, []).append(record)
    return record

def get_latest(project_id: str, artifact_type: str) -> Optional[Dict[str, Any]]:
    """
    Return latest normalized record (adds 'approved' for backend too).
    """
    if _HAS_BACKEND:
        pid, phid = _current_ids(project_id)
        rec = _get_latest(pid, artifact_type, phase_id=phid)
        if not rec:
            return None
        return {
            "id": rec["artifact_id"],
            "ts": rec.get("updated_at", int(time.time())),
            "project_id": pid,
            "artifact_type": rec["type"],
            "data": rec.get("data", {}),
            "approved": str(rec.get("status", "")).lower() == "approved",
            "stage": rec.get("phase_id"),
            "meta": {"workstream": rec.get("workstream")},
        }

    store = _ss()
    key = (project_id, artifact_type)
    if key not in store or not store[key]:
        return None
    return sorted(store[key], key=lambda r: r["ts"])[-1]

def approve_artifact(project_id: str, artifact_type: str) -> bool:
    """
    Approve the latest artifact of this type in the current phase.
    """
    if _HAS_BACKEND:
        pid, phid = _current_ids(project_id)
        latest = _get_latest(pid, artifact_type, phase_id=phid)
        if not latest:
            return False
        _approve_artifact(pid, latest["artifact_id"])
        return True

    store = _ss()
    rec = get_latest(project_id, artifact_type)
    if not rec:
        return False
    rec["approved"] = True
    return True

def list_required_artifacts(phase_code: str) -> Dict[str, Any]:
    if _HAS_BACKEND:
        return _list_required_artifacts(phase_code)
    return {}
