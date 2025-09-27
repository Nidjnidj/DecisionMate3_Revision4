# config/modules_config.py
from dataclasses import dataclass
from typing import Literal, Dict, List
from types import SimpleNamespace
Industry = Literal["oil_gas"]
Mode = Literal["projects", "ops"]
FEL = Literal["FEL1", "FEL2", "FEL3", "FEL4"]
OpsMode = Literal["daily_ops", "small_projects"]

@dataclass(frozen=True)
class Taxonomy:
    industries: List[Industry]
    modes: List[Mode]
    fel_stages: List[FEL]
    ops_modes: List[OpsMode]

# modules_config.py  — EDIT this block
TAXONOMY = SimpleNamespace(
    industries=[
        "oil_gas",
        "green_energy",
        "it",
        "healthcare",
        "government_infrastructure",   # NEW
        "aerospace_defense",           # NEW
        "manufacturing",               # NEW
    ],
    modes=["projects", "ops"],
    fel_stages=["FEL1", "FEL2", "FEL3", "FEL4"],
    ops_modes=["daily_ops", "small_projects", "call_center"],
    green_project_types=["wind", "solar", "hydrogen"],
)


TAGS: Dict[str, List[str]] = {
    "oil_gas:projects": ["pm_hub", "fel_swimlane", "stage_gates", "kpis"],
    "oil_gas:ops": ["ops_hub", "daily_ops", "small_projects", "kpis"],
}
