# services/history.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
import time

from data.firestore import load_project_doc, save_project_doc

MAX_HISTORY = 200  # keep last N snapshots per doc_key

def _hist_key(doc_key: str) -> str:
    return f"history__{doc_key}"

def append_snapshot(
    username: str,
    namespace: str,
    project_id: str,
    doc_key: str,
    snapshot: Dict[str, Any],
) -> None:
    hist_key = _hist_key(doc_key)
    current: Optional[Dict[str, Any]] = load_project_doc(username, namespace, project_id, hist_key)
    items: List[Dict[str, Any]] = current.get("items", []) if isinstance(current, dict) else []
    items.append({"ts": time.time(), "data": snapshot})
    items = items[-MAX_HISTORY:]
    save_project_doc(username, namespace, project_id, hist_key, {"items": items})

def get_history(
    username: str,
    namespace: str,
    project_id: str,
    doc_key: str,
) -> List[Dict[str, Any]]:
    hist_key = _hist_key(doc_key)
    current: Optional[Dict[str, Any]] = load_project_doc(username, namespace, project_id, hist_key)
    if isinstance(current, dict) and isinstance(current.get("items"), list):
        return current["items"]
    return []
import streamlit as st

def render_timeline(industry: str, phase_code: str):
    st.markdown("### ⏳ Timeline")

    arts = st.session_state.get("artifact_registry", {}).get((industry, phase_code), {})

    if not arts:
        st.info("No timeline data available.")
        return

    for key, val in arts.items():
        st.markdown(f"**{key}** — {val.get('status', 'Unknown')}")

    st.caption("This is a minimal placeholder timeline.")
