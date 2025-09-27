# services/gates.py
from __future__ import annotations
from typing import Dict, List, Any
import streamlit as st
from data.firestore import load_project_doc, save_project_doc

# ---- Gate templates (tweak as you like) ----
GATE_ITEMS: Dict[str, List[str]] = {
    "FEL1": [
        "Problem framing approved",
        "High-level scope defined",
        "ROM CAPEX & schedule drafted",
        "Top risks identified",
        "Proceed to FEL2 decision recorded",
    ],
    "FEL2": [
        "Concept options compared",
        "Process scheme selected",
        "Equipment list baseline",
        "L2 schedule & key milestones",
        "Proceed to FEL3 decision recorded",
    ],
    "FEL3": [
        "Issued-for-Review drawings set",
        "±15% estimate complete",
        "Contracting strategy chosen",
        "Execution plan drafted",
        "Proceed to FEL4 decision recorded",
    ],
    "FEL4": [
        "IFC packages prepared",
        "HSE review & actions closed",
        "Interface matrix finalized",
        "Commissioning strategy set",
        "FDP / Investment decision recorded",
    ],
}

def gate_doc_key(fel_stage: str) -> str:
    return f"gate_{fel_stage}"

def load_gate_state(username: str, industry: str, project_id: str, fel_stage: str) -> Dict[str, Any]:
    ns = f"{industry}:projects"
    dk = gate_doc_key(fel_stage)
    return load_project_doc(username, ns, project_id, dk) or {"checked": []}

def save_gate_state(username: str, industry: str, project_id: str, fel_stage: str, checked: List[str]) -> Dict[str, Any]:
    ns = f"{industry}:projects"
    dk = gate_doc_key(fel_stage)
    return save_project_doc(username, ns, project_id, dk, {"checked": checked})
