# firebase_db.py — Rev4 compatibility shim for Rev3 modules (with completion marking)
from __future__ import annotations
from typing import Any, Dict, Optional
import time
import streamlit as st

from data.firestore import save_doc, load_doc
from services.milestones import mark_done

def _compute_namespace() -> str:
    industry = st.session_state.get("industry", "oil_gas")
    mode = st.session_state.get("mode", "projects")
    if mode == "ops":
        ops_mode = st.session_state.get("ops_mode", "daily_ops")
        return f"{industry}:ops:{ops_mode}"
    return f"{industry}:projects"

def _maybe_mark_completion() -> None:
    """If a current tool is open and a project is active, mark it completed."""
    try:
        tool = st.session_state.get("__current_tool")
        project_id = st.session_state.get("active_project_id")
        username = st.session_state.get("username", "Guest")
        if tool and project_id:
            namespace = _compute_namespace()
            mark_done(username, namespace, project_id, tool["module_path"], tool["entry"])
    except Exception:
        pass

# Rev3-style helpers some modules call
def save_project(username: str, doc_key: str, data: Dict[str, Any]) -> Dict[str, Any]:
    res = save_doc(username, doc_key, data)
    _maybe_mark_completion()
    return res

def load_project_data(username: str, doc_key: str) -> Optional[Dict[str, Any]]:
    return load_doc(username, doc_key)

# Generic helpers some modules used
def save_to_firebase(path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    key = path.replace("/", "__")
    res = save_doc("Guest", key, data)
    _maybe_mark_completion()
    return res

def load_from_firebase(path: str) -> Optional[Dict[str, Any]]:
    key = path.replace("/", "__")
    return load_doc("Guest", key)

def log_user_activity(action: str, meta: Optional[Dict[str, Any]] = None) -> None:
    _ = (action, meta, time.time())
# --- Compatibility shims for legacy modules expecting save_project/load_all_projects ---

# Optional: a tiny in-memory index if Firestore is not wired
try:
    _MEM_INDEX = st.session_state.setdefault("_mem_projects_index", {})
except Exception:
    _MEM_INDEX = {}

def save_project(collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a simulation (or any document) under <collection>/<doc_id>.
    Also maintains a simple index so load_all_projects can list them.
    """
    key = f"{collection}__{doc_id}"
    res = None
    try:
        res = save_doc("Guest", key, data)
    except Exception:
        # No Firestore backend? keep a memory copy
        _MEM_INDEX.setdefault(collection, {})
        _MEM_INDEX[collection][doc_id] = {"data": data, "saved_at": time.time()}

    # Maintain an index document for listing
    idx_key = f"index__{collection}"
    try:
        idx = load_doc("Guest", idx_key) or {"items": []}
        items = [it for it in idx.get("items", []) if it.get("id") != doc_id]
        items.append({"id": doc_id, "saved_at": time.time()})
        idx["items"] = items
        try:
            save_doc("Guest", idx_key, idx)
        except Exception:
            # mirror to memory index too
            _MEM_INDEX.setdefault(collection, {})
            _MEM_INDEX[collection].setdefault("_index", []).append({"id": doc_id, "saved_at": time.time()})
    except Exception:
        # No load_doc available; still keep memory index
        _MEM_INDEX.setdefault(collection, {})
        _MEM_INDEX[collection].setdefault("_index", []).append({"id": doc_id, "saved_at": time.time()})

    # If you had a completion hook, keep calling it
    try:
        _maybe_mark_completion()
    except Exception:
        pass
    return res or {"key": key, "data": data}

def load_all_projects(collection: str):
    """
    Return a list of {'id': <doc_id>, 'data': <document>} for the given collection.
    Works with Firestore if configured; otherwise uses in-memory copies saved via save_project.
    """
    items = []
    idx_key = f"index__{collection}"
    used_backend = False

    # Try Firestore-backed index first
    try:
        idx = load_doc("Guest", idx_key)
        if idx and "items" in idx:
            for it in idx["items"]:
                doc_id = it.get("id")
                if not doc_id:
                    continue
                try:
                    doc = load_doc("Guest", f"{collection}__{doc_id}")
                    if doc is not None:
                        items.append({"id": doc_id, "data": doc})
                        used_backend = True
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback to memory if backend not used / empty
    if not used_backend:
        coll = _MEM_INDEX.get(collection, {})
        # explicit index list if present
        for it in coll.get("_index", []):
            did = it.get("id")
            if did and did in coll:
                items.append({"id": did, "data": coll[did]["data"]})
        # or all keys except the index key
        for did, payload in coll.items():
            if did == "_index":
                continue
            if isinstance(payload, dict) and "data" in payload:
                items.append({"id": did, "data": payload["data"]})

    return items
