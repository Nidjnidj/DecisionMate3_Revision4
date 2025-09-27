# services/milestones.py
from __future__ import annotations
from typing import Dict, Any, Set
import time
import streamlit as st
from data.firestore import load_project_doc, save_project_doc

def _compute_namespace(industry: str) -> str:
    mode = st.session_state.get("mode", "projects")
    if mode == "ops":
        ops_mode = st.session_state.get("ops_mode", "daily_ops")
        return f"{industry}:ops:{ops_mode}"
    return f"{industry}:projects"

def _key(module_path: str, entry: str) -> str:
    return f"{module_path}.{entry}"

def get_done_set(username: str, namespace: str, project_id: str) -> Set[str]:
    """Return set of 'module_path.entry' that have been saved at least once."""
    payload = load_project_doc(username, namespace, project_id, "completed_tools") or {}
    items: Dict[str, float] = payload.get("items", {}) if isinstance(payload, dict) else {}
    return set(items.keys())

def mark_done(username: str, namespace: str, project_id: str, module_path: str, entry: str) -> None:
    """Mark a tool as completed (saved at least once)."""
    doc_key = "completed_tools"
    data = load_project_doc(username, namespace, project_id, doc_key) or {"items": {}}
    items: Dict[str, float] = data.get("items", {})
    items[_key(module_path, entry)] = time.time()
    data["items"] = items
    save_project_doc(username, namespace, project_id, doc_key, data)
