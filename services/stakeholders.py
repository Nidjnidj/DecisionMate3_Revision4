# services/stakeholders.py
# CONTEXT: DecisionMate Rev4 – services layer (no UI).
# RULES: pure functions; Streamlit session_state fallback; Firestore wiring optional later.

from __future__ import annotations

from typing import List, Dict, Optional, TypedDict
import uuid
import streamlit as st

# ---------- Robust schema import / fallback ----------
# Try real schema first, otherwise define a compatible TypedDict that matches
# how this service actually stores stakeholders (see add_stakeholder below).
try:
    from decisionmate_core.schemas import Stakeholder  # type: ignore
except Exception:
    class Stakeholder(TypedDict, total=False):
        id: str
        name: str
        role: str
        org: Optional[str]
        email: Optional[str]
        influence: int           # 1..5 (was "power" in some older UIs)
        interest: int            # 1..5
        support: int             # -5..+5
        owner: Optional[str]     # e.g., account manager
        next_touch: Optional[str]  # ISO date or free text
        notes: Optional[str]

__all__ = [
    "Stakeholder",
    "list_stakeholders",
    "get_stakeholder",
    "add_stakeholder",
    "update_stakeholder",
    "delete_stakeholder",
]

_STATE_KEY = "rev4_stakeholders"


# ---------- Internal state ----------
def _state() -> List[Stakeholder]:
    # We store a simple list of Stakeholder dicts in session_state.
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = []  # type: ignore[assignment]
    return st.session_state[_STATE_KEY]


# ---------- CRUD ----------
def list_stakeholders() -> List[Stakeholder]:
    """Return all stakeholders."""
    return list(_state())


def get_stakeholder(stakeholder_id: str) -> Optional[Stakeholder]:
    for s in _state():
        if s.get("id") == stakeholder_id:
            return s
    return None


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def add_stakeholder(data: Dict) -> Stakeholder:
    """
    Create and store a stakeholder. Missing optional fields are filled
    with sensible defaults matching the UI panels.
    """
    new: Stakeholder = {
        "id": data.get("id") or str(uuid.uuid4()),
        "name": str(data.get("name", "")).strip(),
        "org": str(data.get("org", "")).strip() or None,
        "role": str(data.get("role", "")).strip(),
        "email": (str(data.get("email")).strip() if data.get("email") else None),
        "influence": _as_int(data.get("influence", 3), 3),
        "interest": _as_int(data.get("interest", 3), 3),
        "support": _as_int(data.get("support", 0), 0),
        "owner": (str(data.get("owner")).strip() if data.get("owner") else None),
        "next_touch": (str(data.get("next_touch")).strip() if data.get("next_touch") else None),
        "notes": str(data.get("notes", "")).strip() or None,
    }

    # Minimal validation: require a name
    if not new["name"]:
        # Keep it resilient: auto-name if empty
        new["name"] = f"Stakeholder {new['id'][:8]}"

    _state().append(new)
    return new


def update_stakeholder(stakeholder_id: str, patch: Dict) -> Optional[Stakeholder]:
    s = get_stakeholder(stakeholder_id)
    if not s:
        return None

    # Normalize numeric fields if present in the patch
    if "influence" in patch:
        patch["influence"] = _as_int(patch.get("influence"), s.get("influence", 3))
    if "interest" in patch:
        patch["interest"] = _as_int(patch.get("interest"), s.get("interest", 3))
    if "support" in patch:
        patch["support"] = _as_int(patch.get("support"), s.get("support", 0))

    # Normalize empties to None for optional text fields
    for k in ("org", "email", "owner", "next_touch", "notes"):
        if k in patch:
            v = patch.get(k)
            patch[k] = (str(v).strip() or None) if v is not None else None

    s.update(patch)  # type: ignore[arg-type]
    return s


def delete_stakeholder(stakeholder_id: str) -> bool:
    arr = _state()
    idx = next((i for i, s in enumerate(arr) if s.get("id") == stakeholder_id), None)
    if idx is None:
        return False
    del arr[idx]
    return True
