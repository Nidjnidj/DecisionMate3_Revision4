# modules/it_contracts.py
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

# ---- Artifact type constants
IT_BUSINESS_CASE = "it_business_case"
IT_ENGINEERING   = "it_engineering_design"
IT_SCHEDULE      = "it_schedule_plan"
IT_COST          = "it_cost_model"

# ---- Contracts
@dataclass
class BusinessCaseIT:
    project_name: str
    business_owner: str
    problem_statement: str
    goals: List[str]
    success_metrics: List[Dict[str, Any]]  # [{name, target, unit}]
    options: List[Dict[str, Any]]          # [{name, description, capex_est, opex_est, duration_months, risk}]
    selected_option: str
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    expected_benefits: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class EngineeringDesignIT:
    architecture_choice: str                  # e.g., Monolith / Microservices / Serverless
    key_components: List[Dict[str, str]]      # [{name, type}]
    integration_points: List[str]
    nfrs: List[str]                            # Non-functional requirements
    team_setup: List[Dict[str, Any]]          # [{role, count}]
    backlog_story_points: int
    environments: List[str]                   # ["dev","test","staging","prod"]
    dependencies: List[str]
    risks: List[str]
    upstream_refs: List[str]                  # artifact ids/types (business case)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ITSprintSchedule:
    methodology: str                           # Scrum / Kanban (we’ll compute for Scrum)
    sprint_length_weeks: int
    velocity_sp_per_sprint: int
    total_story_points: int
    number_of_sprints: int
    start_date: str                            # ISO yyyy-mm-dd
    release_dates: List[str]                   # list of ISO dates per sprint end
    milestones: List[Dict[str, str]]           # [{name, date}]
    resource_plan: List[Dict[str, Any]]        # [{role, FTE}]
    upstream_refs: List[str]                   # business/eng ids/types

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ITCostModel:
    capex_init: float                          # one-time: licensing, setup
    opex_per_month: Dict[str, float]           # {"cloud":..., "support":..., "people":...}
    months: int
    total_12m: float
    total_36m: float
    burn_curve: List[Dict[str, Any]]           # [{month_index, capex, opex_total, cum}]
    upstream_refs: List[str]                   # schedule/engineering ids/types

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
