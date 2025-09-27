# services/stakeholders.py
# CONTEXT: DecisionMate Rev4 – services layer (no UI).
# RULES: pure functions; Streamlit session_state fallback; Firestore wiring optional later.

from __future__ import annotations
from typing import List, Dict, Optional
import uuid
import streamlit as st
from decisionmate_core.schemas import Stakeholder

_STATE_KEY = "rev4_stakeholders"

def _state() -> List[Stakeholder]:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = []  # type: ignore[assignment]
    return st.session_state[_STATE_KEY]

def list_stakeholders() -> List[Stakeholder]:
    """Return all stakeholders."""
    return list(_state())

def get_stakeholder(stakeholder_id: str) -> Optional[Stakeholder]:
    for s in _state():
        if s["id"] == stakeholder_id:
            return s
    return None

def add_stakeholder(data: Dict) -> Stakeholder:
    """Create and store a stakeholder. Missing optional fields are filled."""
    new: Stakeholder = {
        "id": data.get("id") or str(uuid.uuid4()),
        "name": data.get("name", "").strip(),
        "org": data.get("org", "").strip(),
        "role": data.get("role", "").strip(),
        "influence": int(data.get("influence", 3)),
        "interest": int(data.get("interest", 3)),
        "support": int(data.get("support", 0)),
        "owner": data.get("owner"),
        "next_touch": data.get("next_touch"),
        "notes": data.get("notes", "").strip(),
    }
    _state().append(new)
    return new

def update_stakeholder(stakeholder_id: str, patch: Dict) -> Optional[Stakeholder]:
    s = get_stakeholder(stakeholder_id)
    if not s:
        return None
    s.update(patch)  # type: ignore[arg-type]
    return s

def delete_stakeholder(stakeholder_id: str) -> bool:
    arr = _state()
    idx = next((i for i, s in enumerate(arr) if s["id"] == stakeholder_id), None)
    if idx is None:
        return False
    del arr[idx]
    return True
