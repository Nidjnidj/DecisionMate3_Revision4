# services/kaizen_inbox.py
from __future__ import annotations
import uuid
from typing import List, Dict

try:
    from data.firestore import load_project_doc, save_project_doc
except Exception:
    load_project_doc = save_project_doc = None

def _doc(username: str, namespace: str, project_id: str):
    key = "kaizen_inbox"
    payload = load_project_doc(username, namespace, project_id, key) if load_project_doc else None
    if not payload:
        payload = {"ideas": []}
    return key, payload

def push_suggestions(username: str, namespace: str, project_id: str, ideas: List[Dict]) -> int:
    """
    Append unique suggestions (by 'uid') into kaizen_inbox. Returns number added.
    Expected idea keys: uid, source, title, area, owner, due, benefit, notes
    """
    key, payload = _doc(username, namespace, project_id)
    existing = {i.get("uid") for i in payload.get("ideas", [])}
    added = []
    for idea in ideas:
        uid = idea.get("uid") or str(uuid.uuid4())
        idea["uid"] = uid
        if uid not in existing:
            added.append(idea)
            existing.add(uid)
    if added:
        payload["ideas"].extend(added)
        if save_project_doc:
            save_project_doc(username, namespace, project_id, key, payload)
    return len(added)

def list_suggestions(username: str, namespace: str, project_id: str) -> list:
    key, payload = _doc(username, namespace, project_id)
    return payload.get("ideas", [])

def delete_suggestions(username: str, namespace: str, project_id: str, uids: List[str]) -> int:
    key, payload = _doc(username, namespace, project_id)
    before = len(payload.get("ideas", []))
    payload["ideas"] = [i for i in payload.get("ideas", []) if i.get("uid") not in set(uids)]
    if save_project_doc:
        save_project_doc(username, namespace, project_id, key, payload)
    return before - len(payload.get("ideas", []))
