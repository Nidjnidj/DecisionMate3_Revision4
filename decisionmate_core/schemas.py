# ============================ schemas.py ============================
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import date

class ReservoirPoint(BaseModel):
    t: date
    oil_rate: float = 0.0
    gas_rate: float = 0.0
    water_rate: float = 0.0
    cum_oil: float = 0.0
    cum_gas: float = 0.0
    BHP: Optional[float] = None

class ReservoirProfiles(BaseModel):
    case_id: str
    points: List[ReservoirPoint]

class MBALSummary(BaseModel):
    STOIIP: float
    GIIP: float
    drive_index: Dict[str, float]
    material_balance_fit_score: float

class WellNeedPoint(BaseModel):
    t: date
    required_producers: int
    required_injectors: int
    well_types: Optional[List[str]] = None

class WellNeedPlan(BaseModel):
    case_id: str
    points: List[WellNeedPoint]

class FacilityLoadsPoint(BaseModel):
    t: date
    gas_mmscfd: float
    oil_kbopd: float
    water_kbwpd: float
    export_spec: Optional[str] = None

class FacilityLoads(BaseModel):
    points: List[FacilityLoadsPoint]

class WellCatalogItem(BaseModel):
    well_id: str
    type: Literal["producer","injector"]
    pad: Optional[str] = None
    deviation: Optional[str] = None
    completion: Optional[str] = None
    EUR: Optional[float] = None
    AFE_cost: Optional[float] = None

class WellCatalog(BaseModel):
    wells: List[WellCatalogItem]

class DrillScheduleSeedItem(BaseModel):
    well_id: str
    duration_days: int
    rig: Optional[str] = None
    earliest_start: Optional[date] = None

class DrillScheduleSeed(BaseModel):
    items: List[DrillScheduleSeedItem]

class DrillRisk(BaseModel):
    risk_id: str
    prob: float
    cost_impact: float
    time_impact: float
    phase: str

class DrillRisks(BaseModel):
    items: List[DrillRisk]

class ProcessSimSnapshot(BaseModel):
    streams: List[Dict]
    units: List[Dict]
    duty: Optional[List[Dict]] = None
    pinch: Optional[Dict] = None
    utility_loads: Optional[Dict] = None

class EquipmentSizingItem(BaseModel):
    tag: str
    service: str
    type: str
    duty_or_size: str
    material: Optional[str] = None
    qty: int = 1

class EquipmentSizingList(BaseModel):
    items: List[EquipmentSizingItem]

class BoQItem(BaseModel):
    discipline: str
    item: str
    qty: float
    unit: str
    spec_ref: Optional[str] = None

class BoQPrelim(BaseModel):
    items: List[BoQItem]

class FileRefs(BaseModel):
    files: List[str]

class LLICandidate(BaseModel):
    tag: str
    lead_time_days: int
    vendor_pool: List[str]
    criticality: Literal["low","medium","high"]

class LLICandidates(BaseModel):
    items: List[LLICandidate]

class EngReadiness(BaseModel):
    checklist_scores: Dict[str, float]
    readiness_index: float
    gaps: List[str] = []

class WBSActivity(BaseModel):
    id: str
    name: str
    start: date
    finish: date
    duration: int
    logic: Dict[str, List[str]]
    discipline: str
    cost_code: Optional[str] = None

class WBSActivities(BaseModel):
    activities: List[WBSActivity]

class Milestone(BaseModel):
    id: str
    name: str
    date: date

class Milestones(BaseModel):
    items: List[Milestone]

class ProcurementPlanItem(BaseModel):
    package_id: str
    scope_ref: str
    strategy: Literal["EPC","EPCM","Direct"]
    incoterms: Optional[str] = None
    award_target: Optional[date] = None

class ProcurementPlan(BaseModel):
    items: List[ProcurementPlanItem]

class LLIRegisterItem(BaseModel):
    tag: str
    package_id: str
    RFQ_date: Optional[date] = None
    PO_date: Optional[date] = None
    FAT_date: Optional[date] = None
    ship_date: Optional[date] = None
    on_site_date: Optional[date] = None
    lead_time: Optional[int] = None
    expediting_status: Optional[str] = None

class LLIRegister(BaseModel):
    items: List[LLIRegisterItem]

class VendorScore(BaseModel):
    vendor: str
    score_tech: float
    score_com: float
    delivery_score: float

class VendorMatrix(BaseModel):
    items: List[VendorScore]

class QAQCPlan(BaseModel):
    ITPs: List[str]
    hold_points: List[str]
    inspection_lots: Optional[List[str]] = None

class Workfront(BaseModel):
    area: str
    available_date: date
    pre_reqs: List[str]

class WorkfrontMap(BaseModel):
    items: List[Workfront]

class ProgressPoint(BaseModel):
    t: date
    planned_pct: float
    forecast_pct: float

class ProgressCurve(BaseModel):
    points: List[ProgressPoint]

class CompletionMatrixItem(BaseModel):
    system: str
    sub_system: str
    mech_complete_date: Optional[date] = None
    RFC: Optional[date] = None
    RFSU: Optional[date] = None

class CompletionMatrix(BaseModel):
    items: List[CompletionMatrixItem]

class RiskItem(BaseModel):
    id: str
    cause: str
    event: str
    consequence: str
    P: float
    I_cost: float
    I_time: float
    owner: str
    status: Literal["open","mitigating","closed"]

class RiskRegister(BaseModel):
    items: List[RiskItem]

class Contingency(BaseModel):
    cost_cont_P50: float
    cost_cont_P80: float
    time_buffer_P50: Optional[float] = None
    time_buffer_P80: Optional[float] = None

class TreatmentAction(BaseModel):
    action: str
    owner: str
    due: date
    residual_target: Optional[str] = None

class TreatmentPlan(BaseModel):
    items: List[TreatmentAction]

class CapexItem(BaseModel):
    wbs: str
    base_cost: float
    contingency_from_risk: float
    total: float
    class_code: Optional[str] = Field(None, alias="class")

class CapexWBS(BaseModel):
    items: List[CapexItem]

class CashflowPoint(BaseModel):
    ym: str  # YYYY-MM
    capex: float = 0.0
    opex: float = 0.0

class Cashflow(BaseModel):
    points: List[CashflowPoint]

class OpexPoint(BaseModel):
    t: date
    power: float
    chemicals: float
    maintenance: float
    staffing: float

class OpexProfile(BaseModel):
    points: List[OpexPoint]

class Economics(BaseModel):
    case_id: str
    price_assump: Dict[str, float]
    NPV: float
    IRR: float
    payback: float
    breakeven: Optional[float] = None

class HazardItem(BaseModel):
    node: str
    hazard: str
    barrier: str
    S: int
    L: int
    ALARP: Optional[bool] = None

class HazardRegister(BaseModel):
    items: List[HazardItem]

class QualityObservation(BaseModel):
    package_id: str
    non_conformance: str
    severity: Literal["low","medium","high"]
    closeout_date: Optional[date] = None

class QualityObservations(BaseModel):
    items: List[QualityObservation]

# ---------------- Stakeholder / RACI / Actions ----------------
from typing import TypedDict, List, Literal, Optional

class Stakeholder(TypedDict):
    id: str
    name: str
    org: str
    role: str
    influence: int        # 1..5
    interest: int         # 1..5
    support: int          # -1, 0, 1
    owner: Optional[str]
    next_touch: Optional[str]  # ISO date
    notes: str

RACIRole = Literal["R", "A", "C", "I"]

class RACI(TypedDict):
    R: List[str]
    A: List[str]          # exactly one
    C: List[str]
    I: List[str]

class ActionItem(TypedDict):
    id: str
    type: str                     # "artifact_pending" | "stakeholder_touchpoint" | "generic"
    source_id: str
    title: str
    assignee: Optional[str]
    due: Optional[str]            # ISO date
    status: Literal["open", "done", "dismissed"]
    notes: str
