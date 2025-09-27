# ============================ dependencies.py ============================
from __future__ import annotations
from typing import Dict, List, Set

# Directed acyclic graph of discipline dependencies
DAG: Dict[str, List[str]] = {
    "wells":        ["subsurface"],
    "engineering":  ["subsurface", "wells"],
    "schedule":     ["engineering", "wells", "procurement:milestones?"],  # soft link example
    "procurement":  ["engineering", "schedule"],
    "construction": ["procurement", "schedule"],
    "cost":         ["engineering", "schedule", "risk"],
    "economics":    ["subsurface", "cost", "opex_profile"],
    "risk":         ["subsurface","wells","engineering","procurement","construction","schedule","cost"],
}

# artifact_type -> produced_by discipline (used for propagation)
PRODUCER: Dict[str, str] = {
    # Subsurface
    "reservoir_profiles": "subsurface",
    "mbal_summary": "subsurface",
    "well_need_plan": "subsurface",
    "facility_loads": "subsurface",
    "subsurface_assumptions": "subsurface",

    # Wells
    "well_catalog": "wells",
    "drill_schedule_seed": "wells",
    "drill_risks": "wells",

    # Engineering
    "process_sim_snapshot": "engineering",
    "equipment_sizing_list": "engineering",
    "BoQ_prelim": "engineering",
    "pfd_refs": "engineering",
    "pid_refs": "engineering",
    "LLI_candidates": "engineering",
    "eng_readiness": "engineering",

    # Schedule
    "wbs_activities": "schedule",
    "milestones": "schedule",
    "critical_path_ids": "schedule",
    "risk_time_buffer": "schedule",
    "phase_takt_map": "schedule",

    # Procurement
    "proc_plan": "procurement",
    "LLI_register": "procurement",
    "vendor_matrix": "procurement",
    "qa_qc_plan": "procurement",

    # Construction & Commissioning
    "workfront_map": "construction",
    "progress_curve": "construction",
    "completion_matrix": "construction",

    # Risk
    "risk_register": "risk",
    "contingency": "risk",
    "treatment_plan": "risk",

    # Cost & Finance
    "capex_wbs": "cost",
    "cashflow": "cost",
    "opex_profile": "cost",
    "economics": "finance",

    # HSE/Quality
    "hazard_register": "hse_quality",
    "quality_observations": "hse_quality",
}


def downstream_of(discipline: str) -> Set[str]:
    """Return all disciplines that (transitively) depend on `discipline`."""
    rev: Dict[str, List[str]] = {}
    for node, parents in DAG.items():
        for p in parents:
            key = p.split(":")[0]  # ignore soft qualifiers
            rev.setdefault(key, []).append(node)
    out: Set[str] = set()
    def dfs(x: str):
        for child in rev.get(x, []):
            if child not in out:
                out.add(child)
                dfs(child)
    dfs(discipline)
    return out
