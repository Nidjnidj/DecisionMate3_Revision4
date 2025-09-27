import streamlit as st

# IT Gate Requirements
IT_GATE_CHECK = {
    "FEL1": [ {"workstream": "PMO",         "type": "it_business_case"} ],
    "FEL2": [ {"workstream": "Architecture","type": "it_engineering_design"} ],
    "FEL3": [ {"workstream": "Delivery",    "type": "it_schedule_plan"} ],
    "FEL4": [ {"workstream": "Finance",     "type": "it_cost_model"} ],
}

HEALTHCARE_GATE_CHECK = {
    "FEL1": [
        {"workstream": "Clinical",    "type": "Clinical_Workflow_Charter"},
        {"workstream": "Compliance",  "type": "HIPAA_Assessment"},
        {"workstream": "Schedule",    "type": "WBS"},
        {"workstream": "Finance",     "type": "Cost_Model"},
        {"workstream": "Risk",        "type": "Risk_Register"},
    ],
    "FEL2": [
        {"workstream": "Engineering", "type": "Facility_Design_Package"},
        {"workstream": "IT",          "type": "EMR_Integration_Concept"},
        {"workstream": "Schedule",    "type": "Schedule_Network"},
        {"workstream": "Finance",     "type": "Cost_Model"},
    ],
    "FEL3": [
        {"workstream": "Engineering", "type": "Defined_Clinical_Concept"},
        {"workstream": "Schedule",    "type": "Schedule_Network"},
        {"workstream": "Finance",     "type": "Cost_Model"},
        {"workstream": "Risk",        "type": "Risk_Register"},
    ],
}

GREEN_GATE_CHECK = {
    "FEL1": [
        {"workstream": "Resource", "type": "Wind_Resource_Profile"},
        {"workstream": "Engineering", "type": "Wind_Turbine_Layout"},
        {"workstream": "Engineering", "type": "Wind_Energy_Yield"},
        {"workstream": "Schedule", "type": "WBS"},
        {"workstream": "Risk", "type": "Risk_Register"},
    ],
    "FEL2": [
        {"workstream": "Engineering", "type": "Defined_Concept"},
        {"workstream": "Schedule", "type": "Schedule_Network"},
        {"workstream": "Finance", "type": "Cost_Model"},
        {"workstream": "Risk", "type": "Risk_Register"},
    ],
    "FEL3": [
        {"workstream": "Engineering", "type": "Execution_Concept"},
        {"workstream": "Schedule", "type": "Schedule_Network"},
        {"workstream": "Finance", "type": "Cost_Model"},
        {"workstream": "Risk", "type": "Risk_Register"},
    ],
    "FEL4": [
        {"workstream": "Engineering", "type": "Execution_Concept"},
        {"workstream": "Schedule", "type": "Schedule_Network"},
        {"workstream": "Finance", "type": "Cost_Model"},
    ],
}

ARCH_CONS_REQUIRED = {
    "fel1": [
        {"workstream": "Planning",    "type": "Program_Brief"},
        {"workstream": "Site",        "type": "Site_Screener"},
        {"workstream": "Design",      "type": "Concept_Design_Kit"},
        {"workstream": "Schedule",    "type": "WBS"},
        {"workstream": "Risk",        "type": "Risk_Register"},
    ],
    "fel2": [
        {"workstream": "Design",      "type": "BIM_Lite"},
        {"workstream": "Design",      "type": "Footprint_Estimate"},
        {"workstream": "Cost",        "type": "ROM_Cost_Model"},
        {"workstream": "Schedule",    "type": "L2_L3_Schedule_Draft"},
    ],
    "fel3": [
        {"workstream": "Procurement", "type": "Procurement_Packages"},
        {"workstream": "Quality",     "type": "QA_QC_Plan"},
        {"workstream": "HSE",         "type": "HSE_Plan"},
    ],
    "fel4": [
        {"workstream": "Commissioning","type": "Commissioning_Readiness"},
        {"workstream": "Handover",     "type": "AsBuilt_OM"},
        {"workstream": "Handover",     "type": "Handover_Checklist"},
    ],
}


MANUFACTURING_GATE_CHECK = {
    "FEL1": [  # Screening
        {"workstream": "PMO",        "type": "MFG_Business_Case"},
    ],
    "FEL2": [  # Pre-FEED (Concept)
        {"workstream": "Engineering", "type": "Factory_Sizing"},
        {"workstream": "Engineering", "type": "Layout_Concept"},
        {"workstream": "PMO",         "type": "Site_Shortlist"},
    ],
    "FEL3": [  # FEED (Definition)
        {"workstream": "Schedule",    "type": "WBS"},
        {"workstream": "Schedule",    "type": "Schedule_Network"},
        {"workstream": "Finance",     "type": "Cost_Model"},
    ],
    "FEL4": [  # Execution & Detail Design
        {"workstream": "Engineering", "type": "Procurement_Packages"},
        {"workstream": "PMO",         "type": "Construction_Plan"},
        {"workstream": "PMO",         "type": "Commissioning_Plan"},
    ],
}

import streamlit as st

# IT Gate Requirements
IT_GATE_CHECK = {
    "FEL1": [ {"workstream": "PMO",         "type": "it_business_case"} ],
    "FEL2": [ {"workstream": "Architecture","type": "it_engineering_design"} ],
    "FEL3": [ {"workstream": "Delivery",    "type": "it_schedule_plan"} ],
    "FEL4": [ {"workstream": "Finance",     "type": "it_cost_model"} ],
}

HEALTHCARE_GATE_CHECK = {
    "FEL1": [
        {"workstream": "Clinical",    "type": "Clinical_Workflow_Charter"},
        {"workstream": "Compliance",  "type": "HIPAA_Assessment"},
        {"workstream": "Schedule",    "type": "WBS"},
        {"workstream": "Finance",     "type": "Cost_Model"},
        {"workstream": "Risk",        "type": "Risk_Register"},
    ],
    "FEL2": [
        {"workstream": "Engineering", "type": "Facility_Design_Package"},
        {"workstream": "IT",          "type": "EMR_Integration_Concept"},
        {"workstream": "Schedule",    "type": "Schedule_Network"},
        {"workstream": "Finance",     "type": "Cost_Model"},
    ],
    "FEL3": [
        {"workstream": "Engineering", "type": "Defined_Clinical_Concept"},
        {"workstream": "Schedule",    "type": "Schedule_Network"},
        {"workstream": "Finance",     "type": "Cost_Model"},
        {"workstream": "Risk",        "type": "Risk_Register"},
    ],
}

GREEN_GATE_CHECK = {
    "FEL1": [
        {"workstream": "Resource", "type": "Wind_Resource_Profile"},
        {"workstream": "Engineering", "type": "Wind_Turbine_Layout"},
        {"workstream": "Engineering", "type": "Wind_Energy_Yield"},
        {"workstream": "Schedule", "type": "WBS"},
        {"workstream": "Risk", "type": "Risk_Register"},
    ],
    "FEL2": [
        {"workstream": "Engineering", "type": "Defined_Concept"},
        {"workstream": "Schedule", "type": "Schedule_Network"},
        {"workstream": "Finance", "type": "Cost_Model"},
        {"workstream": "Risk", "type": "Risk_Register"},
    ],
    "FEL3": [
        {"workstream": "Engineering", "type": "Execution_Concept"},
        {"workstream": "Schedule", "type": "Schedule_Network"},
        {"workstream": "Finance", "type": "Cost_Model"},
        {"workstream": "Risk", "type": "Risk_Register"},
    ],
    "FEL4": [
        {"workstream": "Engineering", "type": "Execution_Concept"},
        {"workstream": "Schedule", "type": "Schedule_Network"},
        {"workstream": "Finance", "type": "Cost_Model"},
    ],
}

ARCH_CONS_REQUIRED = {
    "fel1": [
        {"workstream": "Planning",    "type": "Program_Brief"},
        {"workstream": "Site",        "type": "Site_Screener"},
        {"workstream": "Design",      "type": "Concept_Design_Kit"},
        {"workstream": "Schedule",    "type": "WBS"},
        {"workstream": "Risk",        "type": "Risk_Register"},
    ],
    "fel2": [
        {"workstream": "Design",      "type": "BIM_Lite"},
        {"workstream": "Design",      "type": "Footprint_Estimate"},
        {"workstream": "Cost",        "type": "ROM_Cost_Model"},
        {"workstream": "Schedule",    "type": "L2_L3_Schedule_Draft"},
    ],
    "fel3": [
        {"workstream": "Procurement", "type": "Procurement_Packages"},
        {"workstream": "Quality",     "type": "QA_QC_Plan"},
        {"workstream": "HSE",         "type": "HSE_Plan"},
    ],
    "fel4": [
        {"workstream": "Commissioning","type": "Commissioning_Readiness"},
        {"workstream": "Handover",     "type": "AsBuilt_OM"},
        {"workstream": "Handover",     "type": "Handover_Checklist"},
    ],
}


MANUFACTURING_GATE_CHECK = {
    "FEL1": [  # Screening
        {"workstream": "PMO",        "type": "MFG_Business_Case"},
    ],
    "FEL2": [  # Pre-FEED (Concept)
        {"workstream": "Engineering", "type": "Factory_Sizing"},
        {"workstream": "Engineering", "type": "Layout_Concept"},
        {"workstream": "PMO",         "type": "Site_Shortlist"},
    ],
    "FEL3": [  # FEED (Definition)
        {"workstream": "Schedule",    "type": "WBS"},
        {"workstream": "Schedule",    "type": "Schedule_Network"},
        {"workstream": "Finance",     "type": "Cost_Model"},
    ],
    "FEL4": [  # Execution & Detail Design
        {"workstream": "Engineering", "type": "Procurement_Packages"},
        {"workstream": "PMO",         "type": "Construction_Plan"},
        {"workstream": "PMO",         "type": "Commissioning_Plan"},
    ],
}

def list_required_artifacts_industry_aware(phase_code: str, industry: str):
    """Return required artifacts per phase depending on selected industry."""
    # normalize inputs so 'FEL1'/'fel1' both work, and industry keys are stable
    ind = (industry or "").lower()
    ph  = (phase_code or "").lower()

    # --- Specific industries ---
    if ind == "it":
        return IT_GATE_CHECK.get(phase_code, [])          # IT dict uses 'FEL1' keys
    if ind == "green_energy":
        return GREEN_GATE_CHECK.get(phase_code, [])       # GREEN dict uses 'FEL#' keys
    if ind == "healthcare":
        return HEALTHCARE_GATE_CHECK.get(phase_code, [])  # HEALTHCARE uses 'FEL#'
    if ind == "manufacturing":
        return MANUFACTURING_GATE_CHECK.get(phase_code, [])

    # NEW: Architecture & Construction (your keys are lowercased: 'fel1', ...).
    if ind in ("arch_construction", "architecture_construction"):
        return ARCH_CONS_REQUIRED.get(ph, [])

    # --- Generic (no-subsurface) fallback for other non-O&G industries ---
    GENERIC_NO_SUBSURFACE = {
        "FEL1": [
            {"workstream": "Engineering", "type": "Defined_Concept"},
            {"workstream": "Schedule",    "type": "WBS"},
            {"workstream": "Finance",     "type": "Cost_Model"},
            {"workstream": "Risk",        "type": "Risk_Register"},
        ],
        "FEL2": [
            {"workstream": "Engineering", "type": "Execution_Concept"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Finance",     "type": "Cost_Model"},
        ],
        "FEL3": [
            {"workstream": "Engineering", "type": "Execution_Concept"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Finance",     "type": "Cost_Model"},
        ],
        "FEL4": [
            {"workstream": "Engineering", "type": "Execution_Concept"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Finance",     "type": "Cost_Model"},
        ],
    }
    # Use the original case for this table
    return GENERIC_NO_SUBSURFACE.get(phase_code, [])
