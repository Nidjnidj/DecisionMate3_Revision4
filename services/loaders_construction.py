
from typing import Dict, Any
from services.artifact_service import ArtifactService

def schedule_inputs_from_design(svc: ArtifactService) -> Dict[str, Any]:
    return {"design_package": svc.latest("design_package")}

def procurement_inputs_from_design(svc: ArtifactService) -> Dict[str, Any]:
    return {"design_package": svc.latest("design_package")}

def construction_inputs_from_sched_and_proc(svc: ArtifactService) -> Dict[str, Any]:
    return {"master_schedule": svc.latest("master_schedule"), "procurement_plan": svc.latest("procurement_plan")}
