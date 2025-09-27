import streamlit as st

STAGE_DEFAULT_DELIVERABLES = {
    "FEL1": [
        "Reservoir Profiles (Subsurface)",
        "Reference Case Identification (Engineering)",
        "WBS (Schedule)",
        "Schedule Network (Schedule)",
        "Long Lead Item List (Procurement)",
        "Initial Cost Model (Finance)",
        "Risk Register Baseline (Risk)"
    ],
    "FEL2": [
        "Reservoir Profiles Update (Subsurface)",
        "Concept Selected Package (Engineering)",
        "Updated WBS (Schedule)",
        "Updated Schedule Network (Schedule)",
        "Updated Long Lead Item List (Procurement)",
        "Refined Cost Model (Finance)",
        "Risk Register Update (Risk)"
    ],
    "FEL3": [
        "Reservoir Profiles – Validation (Subsurface)",
        "Defined Concept Package (Engineering)",
        "Level-3 WBS (Schedule)",
        "Integrated Schedule (Schedule)",
        "LLI & Procurement Plan (Procurement)",
        "Control Cost Model (Finance)",
        "Risk Response Plan (Risk)"
    ],
    "FEL4": [
        "Reservoir Profiles – Handover (Subsurface)",
        "Execution Concept Package (Engineering)",
        "Execution WBS (Schedule)",
        "Execution Schedule (Schedule)",
        "Procurement Execution List (Procurement)",
        "Final Cost Model (Finance)",
        "Risk Watchlist (Risk)"
    ]
}

REQUIRED_ARTIFACTS_STAGE = {
    "FEL1": ["Reservoir_Profiles", "Reference_Case_Identification", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
    "FEL2": ["Reservoir_Profiles", "Concept_Selected", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
    "FEL3": ["Reservoir_Profiles", "Defined_Concept", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"],
    "FEL4": ["Reservoir_Profiles", "Execution_Concept", "WBS", "Schedule_Network", "Long_Lead_List", "Cost_Model", "Risk_Register"]
}

def ensure_stage_default_deliverables(stage: str, session_state):
    if not session_state.deliverables.get(stage):
        session_state.deliverables[stage] = [
            {"name": n, "status": "In Progress"} for n in STAGE_DEFAULT_DELIVERABLES.get(stage, [])
        ]