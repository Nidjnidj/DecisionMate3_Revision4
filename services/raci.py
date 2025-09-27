# services/raci.py
# CONTEXT: DecisionMate Rev4 – services layer (no UI).
from __future__ import annotations
from typing import Dict, Optional
import streamlit as st
from decisionmate_core.schemas import RACI

_STATE_KEY = "rev4_raci_by_artifact"

def _state() -> Dict[str, RACI]:
    if _STATE_KEY not in st.session_state:
        st.session_state[_STATE_KEY] = {}  # type: ignore[assignment]
    return st.session_state[_STATE_KEY]

def get_raci(artifact_id: str) -> Optional[RACI]:
    return _state().get(artifact_id)

def set_raci(artifact_id: str, raci: RACI) -> RACI:
    # Validate A has exactly one owner
    if not raci.get("A") or len(raci["A"]) != 1:
        raise ValueError("RACI must have exactly one 'A' (Accountable) user.")
    _state()[artifact_id] = raci
    return raci
