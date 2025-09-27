# services/moc.py
# CONTEXT: DecisionMate Rev4 – services layer (no UI).
from __future__ import annotations
from typing import List, Dict, Optional
import uuid
import streamlit as st

_STATE_KEY = "rev4_moc"

def _state() -> List[Dict]:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = []  # type: ignore[assignment]
    return st.session_state[_STATE_KEY]

def list_moc() -> List[Dict]:
    return list(_state())

def get_moc(moc_id: str | None) -> Optional[Dict]:
    if not moc_id:
        return None
    for r in _state():
        if r["id"] == moc_id:
            return r
    return None

def add_moc(data: Dict) -> Dict:
    new = {
        "id": data.get("id") or str(uuid.uuid4()),
        "title": data.get("title","").strip(),
        "description": data.get("description","").strip(),
        "impacts": list(data.get("impacts", [])),
        "requester": data.get("requester","").strip(),
        "approver": data.get("approver","").strip(),
        "status": data.get("status","open").strip(),  # open | approved | rejected | withdrawn
        "links": list(data.get("links", [])),         # artifact ids, etc.
    }
    _state().append(new)
    return new

def update_moc(moc_id: str, patch: Dict) -> Optional[Dict]:
    r = get_moc(moc_id)
    if not r:
        return None
    r.update(patch)
    return r

def delete_moc(moc_id: str) -> bool:
    arr = _state()
    idx = next((i for i, r in enumerate(arr) if r["id"] == moc_id), None)
    if idx is None:
        return False
    del arr[idx]
    return True
