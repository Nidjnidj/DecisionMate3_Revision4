# data/firestore.py
from __future__ import annotations
import json, os, time
from typing import Any, Dict, Optional

def _local_dir() -> str:
    base = os.path.join(os.getcwd(), "data", "local_store")
    os.makedirs(base, exist_ok=True)
    return base

def _local_path(username: str, doc: str) -> str:
    safe_user = username.replace("/", "_")
    safe_doc = doc.replace("/", "_")
    return os.path.join(_local_dir(), f"{safe_user}__{safe_doc}.json")

def _has_firebase_secrets() -> bool:
    try:
        import streamlit as st  # type: ignore
        _ = st.secrets["firebase"]
        return True
    except Exception:
        return False

# --- Public API ---
def save_doc(username: str, doc: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves a document either to Firestore (if configured) or to local JSON.
    Returns a small status dict.
    """
    if _has_firebase_secrets():
        try:
            import firebase_admin  # type: ignore
            from firebase_admin import credentials, firestore  # type: ignore
            import streamlit as st  # type: ignore

            if not firebase_admin._apps:
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
                firebase_admin.initialize_app(cred)

            db = firestore.client()
            db.collection("rev4_projects").document(username).collection("docs").document(doc).set({
                "data": data,
                "updated_at": time.time(),
            })
            return {"ok": True, "mode": "firestore"}
        except Exception as e:
            # fallback to local if Firestore fails
            pass

    # Local fallback
    path = _local_path(username, doc)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"data": data, "updated_at": time.time()}, f, ensure_ascii=False, indent=2)
    return {"ok": True, "mode": "local", "path": path}

def load_doc(username: str, doc: str) -> Optional[Dict[str, Any]]:
    """
    Loads a document from Firestore when configured; otherwise from local JSON.
    """
    if _has_firebase_secrets():
        try:
            import firebase_admin  # type: ignore
            from firebase_admin import credentials, firestore  # type: ignore
            import streamlit as st  # type: ignore

            if not firebase_admin._apps:
                cred = credentials.Certificate(dict(st.secrets["firebase"]))
                firebase_admin.initialize_app(cred)
            db = firestore.client()
            ref = db.collection("rev4_projects").document(username).collection("docs").document(doc).get()
            if ref.exists:
                payload = ref.to_dict()
                return payload.get("data") if payload else None
        except Exception:
            pass

    path = _local_path(username, doc)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            return payload.get("data")
    return None
# ------- PROJECT INDEX HELPERS -------

# ------- PROJECT INDEX HELPERS (namespaced) -------

def _index_key(username: str, namespace: str) -> str:
    # per-user + per-namespace project list
    return f"{username}__{namespace}__projects_index"

def list_projects(username: str, namespace: str) -> Dict[str, Dict[str, Any]]:
    """
    Returns {project_id: {name: str, created_at: ts}} for this namespace.
    """
    idx = load_doc(username, _index_key(username, namespace)) or {}
    return idx

def create_project(username: str, namespace: str, name: str) -> str:
    import time, re
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower() or "project"
    pid = f"{base}-{int(time.time())}"
    idx = list_projects(username, namespace)
    idx[pid] = {"name": name, "created_at": time.time()}
    save_doc(username, _index_key(username, namespace), idx)
    return pid

def save_project_doc(username: str, namespace: str, project_id: str, doc: str, data: Dict[str, Any]):
    # namespace all saved docs so PM and Ops don’t collide
    return save_doc(username, f"{namespace}__{project_id}__{doc}", data)

def load_project_doc(username: str, namespace: str, project_id: str, doc: str):
    return load_doc(username, f"{namespace}__{project_id}__{doc}")
