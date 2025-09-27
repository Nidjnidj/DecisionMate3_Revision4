# ============================ loaders.py ============================
from __future__ import annotations
from typing import Dict, Any

from .artifact_service import ArtifactService

# Glue loaders – fetch upstream artifacts and present convenient data bags

def engineering_load_from_subsurface(svc: ArtifactService, case_id: str) -> Dict[str, Any]:
    rp = svc.latest("reservoir_profiles")
    fl = svc.latest("facility_loads")
    return {
        "reservoir_profiles": rp.data if rp else None,
        "facility_loads": fl.data if fl else None,
        "case_id": case_id,
    }

def schedule_load_from_engineering(svc: ArtifactService) -> Dict[str, Any]:
    equip = svc.latest("equipment_sizing_list")
    lli_reg = svc.latest("LLI_register")
    lli_cand = svc.latest("LLI_candidates") if not lli_reg else None
    drill = svc.latest("drill_schedule_seed")
    return {
        "equipment_sizing_list": equip.data if equip else None,
        "LLI": (lli_reg.data if lli_reg else (lli_cand.data if lli_cand else None)),
        "drill_schedule_seed": drill.data if drill else None,
    }

def procurement_load_from_engineering_and_schedule(svc: ArtifactService) -> Dict[str, Any]:
    equip = svc.latest("equipment_sizing_list")
    milestones = svc.latest("milestones")
    return {
        "equipment_sizing_list": equip.data if equip else None,
        "milestones": milestones.data if milestones else None,
    }

def construction_load_from_procurement_and_schedule(svc: ArtifactService) -> Dict[str, Any]:
    wbs = svc.latest("wbs_activities")
    lli = svc.latest("LLI_register")
    return {
        "wbs_activities": wbs.data if wbs else None,
        "LLI_register": lli.data if lli else None,
    }

def cost_load_from_schedule_and_eng(svc: ArtifactService) -> Dict[str, Any]:
    wbs = svc.latest("wbs_activities")
    boq = svc.latest("BoQ_prelim")
    equip = svc.latest("equipment_sizing_list")
    cont = svc.latest("contingency")
    return {
        "wbs_activities": wbs.data if wbs else None,
        "BoQ_prelim": boq.data if boq else None,
        "equipment_sizing_list": equip.data if equip else None,
        "contingency": cont.data if cont else None,
    }

def finance_load_from_cost_and_reservoir(svc: ArtifactService) -> Dict[str, Any]:
    cf = svc.latest("cashflow")
    rp = svc.latest("reservoir_profiles")
    opex = svc.latest("opex_profile")
    return {
        "cashflow": cf.data if cf else None,
        "reservoir_profiles": rp.data if rp else None,
        "opex_profile": opex.data if opex else None,
    }

def risk_load_from_everywhere(svc: ArtifactService) -> Dict[str, Any]:
    bundles = {}
    for t in [
        "reservoir_profiles","well_catalog","drill_risks",
        "equipment_sizing_list","LLI_register","wbs_activities",
        "proc_plan","qa_qc_plan","workfront_map"
    ]:
        rec = svc.latest(t)
        if rec:
            bundles[t] = rec.data
    return bundles


def hse_quality_loaders(svc: ArtifactService) -> Dict[str, Any]:
    pfd = svc.latest("pfd_refs")
    pidr = svc.latest("pid_refs")
    qa = svc.latest("qa_qc_plan")
    return {
        "pfd_refs": pfd.data if pfd else None,
        "pid_refs": pidr.data if pidr else None,
        "qa_qc_plan": qa.data if qa else None,
    }

