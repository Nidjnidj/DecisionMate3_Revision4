import streamlit as st
from typing import List, Dict

ENGINEERING_ARTIFACT_BY_STAGE = {
    "FEL1": "Reference_Case_Identification",
    "FEL2": "Concept_Selected",
    "FEL3": "Defined_Concept",
    "FEL4": "Execution_Concept",
}

REQUIRED_ARTIFACTS = {
    "FEL1": ["Reservoir_Profiles", "Reference_Case_Identification", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
    "FEL2": ["Reservoir_Profiles", "Concept_Selected", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
    "FEL3": ["Reservoir_Profiles", "Defined_Concept", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
    "FEL4": ["Reservoir_Profiles", "Execution_Concept", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
}
# What Subsurface must deliver at each FEL stage (used by modules/subsurface.py)
SUBSURFACE_DELIV_BY_STAGE = {
    "FEL1": "Reservoir Profiles (Subsurface)",
    "FEL2": "Reservoir Profiles Update (Subsurface)",
    "FEL3": "Reservoir Profiles – Validation (Subsurface)",
    "FEL4": "Reservoir Profiles – Handover (Subsurface)",
}

def _ensure_deliverable(stage: str, name: str):
    """Ensure a deliverable row exists for the given stage & name."""
    d = st.session_state.setdefault("deliverables", {"FEL1": [], "FEL2": [], "FEL3": [], "FEL4": []})
    arr = d.setdefault(stage, [])
    if not any(d_.get("name") == name for d_ in arr):
        arr.append({"name": name, "status": "In Progress"})

def _mark_deliverable(stage: str, name: str, status: str = "Done"):
    d = st.session_state.setdefault("deliverables", {"FEL1": [], "FEL2": [], "FEL3": [], "FEL4": []})
    arr = d.setdefault(stage, [])
    for row in arr:
        if row.get("name") == name:
            row["status"] = status
            break

def _set_artifact_status(artifact: str, status: str):
    arts = st.session_state.setdefault("artifacts", {})
    arts[artifact] = status
