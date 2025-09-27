# services/pm_bridge.py
from __future__ import annotations
import json, time
from typing import Any, Dict, Optional

try:
    import streamlit as st
except Exception:  # pragma: no cover
    # Allow import without Streamlit at build time
    class _Dummy:
        session_state = {}
        def warning(self, *a, **k): pass
        def info(self, *a, **k): pass
    st = _Dummy()

# --- Firestore (optional) ---
_firestore_ready = False
_db = None
_doc_root = None

try:
    import firebase_admin
    from firebase_admin import firestore
    if getattr(firebase_admin, "_apps", None):
        _db = firestore.client()
        _firestore_ready = True
except Exception:
    _firestore_ready = False


def _project_key() -> str:
    return (
        str(st.session_state.get("project_id")
            or st.session_state.get("project_name")
            or st.session_state.get("active_project")
            or "default_project")
    )


def save_stage(stage: str, payload: Dict[str, Any]) -> None:
    """Persist a stage payload. Uses Firestore if initialized, else st.session_state.
    Stage should be like "fel1", "fel2", ....
    """
    rec = {
        "stage": stage,
        "project": _project_key(),
        "payload": payload,
        "ts": time.time(),
    }

    if _firestore_ready:
        try:
            col = _db.collection("pm_bridge").document(rec["project"]).collection("stages")
            col.document(stage).set(rec)
            return
        except Exception as e:
            st.warning(f"Firestore save failed, using session fallback: {e}")

    # Session fallback
    st.session_state.setdefault("pm_bridge", {})
    st.session_state["pm_bridge"].setdefault(_project_key(), {})
    st.session_state["pm_bridge"][_project_key()][stage] = rec


def load_stage(stage: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load a stage payload or default.
    Returns the record dict {stage, project, payload, ts} or a default-wrapped record.
    """
    if _firestore_ready:
        try:
            doc = (
                _db.collection("pm_bridge")
                   .document(_project_key())
                   .collection("stages")
                   .document(stage)
                   .get()
            )
            if doc and doc.exists:
                return doc.to_dict()
        except Exception:
            pass

    # Session fallback
    rec = (
        st.session_state.get("pm_bridge", {})
            .get(_project_key(), {})
            .get(stage)
    )
    if rec:
        return rec

    return {
        "stage": stage,
        "project": _project_key(),
        "payload": (default or {}),
        "ts": 0.0,
    }