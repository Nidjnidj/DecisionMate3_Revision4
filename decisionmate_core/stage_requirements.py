# ============================ stage_requirements.py ============================
from __future__ import annotations
from typing import Dict, List

# Minimal Viable Artifacts (MVAs) & KPI thresholds per gate
STAGE_REQUIREMENTS: Dict[str, Dict[str, List[str] | Dict[str, float]]] = {
    "FEL1": {
        "artifacts": [
            "mbal_summary", "reservoir_profiles", "facility_loads",
            "process_sim_snapshot", "LLI_candidates",
            "milestones", "capex_wbs"
        ],
        "kpis": {"readiness_index_min": 0.4}
    },
    "FEL2": {
        "artifacts": [
            "reservoir_profiles", "well_need_plan", "well_catalog",
            "process_sim_snapshot", "equipment_sizing_list", "BoQ_prelim",
            "LLI_candidates", "wbs_activities", "critical_path_ids",
            "capex_wbs", "risk_register"
        ],
        "kpis": {"readiness_index_min": 0.6}
    },
    "FEL3": {
        "artifacts": [
            "equipment_sizing_list", "pfd_refs", "pid_refs",
            "LLI_register", "wbs_activities", "qa_qc_plan",
            "capex_wbs", "contingency"
        ],
        "kpis": {"readiness_index_min": 0.75}
    },
    "FEL4": {
        "artifacts": [
            "workfront_map", "progress_curve", "completion_matrix",
            "cashflow", "economics", "hazard_register", "quality_observations"
        ],
        "kpis": {"readiness_index_min": 0.85}
    },
}

