# services/bim_store.py
from __future__ import annotations
import streamlit as st
from typing import List, Dict, Any

ROOMS_KEY = "bim_model"  # {"rooms": [...]}

def save_rooms(rows: List[Dict[str, Any]]):
    st.session_state[ROOMS_KEY] = {"rooms": rows}

def get_rooms() -> List[Dict[str, Any]]:
    return (st.session_state.get(ROOMS_KEY) or {}).get("rooms", [])
