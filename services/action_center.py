# services/action_center.py
# CONTEXT: DecisionMate Rev4 – services layer (no UI).
from __future__ import annotations
from typing import List, Dict, Optional
import uuid
import streamlit as st
from decisionmate_core.schemas import ActionItem

_STATE_KEY = "rev4_action_items"

def _state() -> List[ActionItem]:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = []  # type: ignore[assignment]
    return st.session_state[_STATE_KEY]

def list_actions(status: Optional[str] = None) -> List[ActionItem]:
    items = list(_state())
    if status:
        items = [i for i in items if i["status"] == status]
    # Overdue/near-due sorting can be added later
    return items

def add_action(item: Dict) -> ActionItem:
    new: ActionItem = {
        "id": item.get("id") or str(uuid.uuid4()),
        "type": item.get("type", "generic"),
        "source_id": item.get("source_id", ""),
        "title": item.get("title", "Action"),
        "assignee": item.get("assignee"),
        "due": item.get("due"),
        "status": item.get("status", "open"),
        "notes": item.get("notes", ""),
    }
    _state().append(new)
    return new

def update_action(action_id: str, patch: Dict) -> Optional[ActionItem]:
    for a in _state():
        if a["id"] == action_id:
            a.update(patch)  # type: ignore[arg-type]
            return a
    return None

def complete_action(action_id: str) -> bool:
    return bool(update_action(action_id, {"status": "done"}))
