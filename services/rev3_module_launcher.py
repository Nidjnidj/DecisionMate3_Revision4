import streamlit as st
# =============================================================================
# Rev3 module launcher (static seeds + dynamic discovery)
# =============================================================================
from decisionmate_core.artifact_service import ArtifactService
from decisionmate_core.dependencies import PRODUCER

import importlib
import inspect

REV3_T = {
    "title": "DecisionMate",
    "select_module": "Select Module",
    "group_titles": {}  # your modules read T.get("group_titles", {})
}

def _import_legacy_module(module_path: str):
    base = module_path.split(".")[-1]
    candidates = [module_path, f"modules.{base}", base, f"decisionmate_core.{base}"]
    last_err = None
    for cand in candidates:
        try:
            if importlib.util.find_spec(cand) is not None:
                return importlib.import_module(cand)
        except Exception as e:
            last_err = e
    raise last_err or ModuleNotFoundError(f"Cannot import {module_path}")

def run_legacy(module_path: str, func_name: str):
    """Import legacy module and run with Rev-3 calling convention if available."""
    mod = _import_legacy_module(module_path)
    base = mod.__name__.split(".")[-1]
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        for cand in ("run", "main", base):
            fn = getattr(mod, cand, None)
            if callable(fn):
                break
    if not callable(fn):
        raise RuntimeError(f"No callable entry for {module_path} (tried {func_name}, run, main, {base})")
    sig = inspect.signature(fn)
    try:
        return fn(REV3_T) if len(sig.parameters) >= 1 else fn()
    except TypeError:
        return fn()

# 1) A few curated seeds (keep any you rely on)
REV3_MODULES: dict[str, tuple[str,str]] = {
    "Compressor Power Estimator": ("compressor_estimator", "compressor_estimator"),
    "Heater/Cooler Simulator": ("heater_cooler_sim", "run"),
    "Flash Calculation": ("flash_calc", "flash_calc"),
    "Basis of Design": ("basis_of_design", "basis_of_design"),
    "I/O List Generator": ("io_list_generator", "io_list_generator"),
    "Equipment Comparison": ("equipment_comparison", "equipment_comparison"),
    "Beam Size Recommender": ("beam_size_recommender", "beam_size_recommender"),
    "Foundation Selector": ("foundation_selector", "foundation_selector"),
    "Decline Curve Analyzer": ("decline_curve", "run"),
    "Critical Path Analyzer": ("critical_path", "critical_path"),
    "Burndown Chart": ("burndown_chart", "burndown_chart"),
    "Delivery Milestone Tracker": ("delivery_tracker", "delivery_tracker"),
    "Document Control Tracker": ("document_control_tracker", "run"),
    "Cost Estimator": ("cost_estimator", "cost_estimator"),
    "Financial Analysis": ("financial_analysis", "financial_analysis"),
    "Break-Even Calculator": ("break_even", "break_even"),
    "Construction Progress Tracker": ("construction_progress_tracker", "construction_progress_tracker"),
    "Construction Daily Log": ("construction_daily_log", "construction_daily_log"),
    "Construction Change Tracker": ("construction_change_tracker", "construction_change_tracker"),
    "Construction Equipment Log": ("construction_equipment_log", "construction_equipment_log"),
    "Constructability Review Tool": ("constructability_review_tool", "constructability_review_tool"),
    "Concrete Pour Log": ("concrete_pour_log", "concrete_pour_log"),
    "Equipment Usage Log": ("equipment_usage_log", "equipment_usage_log"),
    "Handover Tracker": ("handover_tracker", "handover_tracker"),
    "Construction Risk Log": ("construction_risk_log", "construction_risk_log"),
    "JSA Builder": ("jsa_builder", "run"),
    "HSE KPI Dashboard": ("hse_kpi_dashboard", "run"),
    "HSE Audit Planner": ("hse_audit_planner", "run"),
    "Incident Report Tool": ("incident_report_tool", "run"),
    "Cognitive Bias Checker": ("bias_checker", "bias_checker"),
    "Interdependency Tracker": ("interdependency_tracker", "interdependency_tracker"),
    "Interface Matrix": ("interface_matrix", "interface_matrix"),
    "Interface Review Summary": ("interface_review", "interface_review"),
    "Discipline Ownership Map": ("discipline_ownership", "discipline_ownership"),
    "Communication Tracker": ("communication_tracker", "communication_tracker"),
    "Engagement Plan Builder": ("engagement_plan", "engagement_plan"),
    "Control Narrative Builder": ("control_narrative", "control_narrative"),
    "DPMO & Sigma Calculator": ("dpmo_calculator", "run"),
    "Goal Planner": ("goal_planner", "goal_planner"),
    "House Layout Planner": ("house_layout_planner", "house_layout_planner"),
    "House Drafting Canvas": ("house_drafting_canvas", "house_drafting_canvas"),
    "Elevation Sketch": ("elevation_sketch", "elevation_sketch"),
}

# === Exact Rev-3 groups: {Group Label: {UI Name: (module_path, func_name)}} ===
REV3_GROUPS = {
    "🧠 Personal Decisions": {
        "LifeCareer": ("modules.life_career", "life_career"),
        "ProsCons": ("modules.pros_cons", "run"),
        "GoalPlanner": ("modules.goal_planner", "run"),
        "RentVsBuy": ("modules.rent_vs_buy", "rent_vs_buy"),
    },
    "📊 Business & Financial": {
        "FinancialAnalysis": ("modules.financial_analysis", "financial_analysis"),
        "BreakEven": ("modules.break_even", "break_even"),
        "CostEstimator": ("modules.cost_estimator", "cost_estimator"),
    },
    "🛠️ Construction": {
        "MaterialEstimator": ("modules.material_estimator", "material_estimator"),
        "ConcreteMixOptimizer": ("modules.concrete_mix_optimizer", "concrete_mix_optimizer"),
        "ConcretePourLog": ("modules.concrete_pour_log", "concrete_pour_log"),
        "EquipmentComparison": ("modules.equipment_comparison", "equipment_comparison"),
        "SteelMaterialTracker": ("modules.steel_material_tracker", "steel_material_tracker"),
        "WorkPackageBuilder": ("modules.work_package_builder", "work_package_builder"),
        "ConstructionDailyLog": ("modules.construction_daily_log", "construction_daily_log"),
        "ManpowerTracker": ("modules.manpower_tracker", "manpower_tracker"),
        "EquipmentUsageLog": ("modules.equipment_usage_log", "equipment_usage_log"),
        "ConstructionMeetingNotes": ("modules.construction_meeting_notes", "construction_meeting_notes"),
        "PunchlistTracker": ("modules.punchlist_tracker", "punchlist_tracker"),
        "HandoverTracker": ("modules.handover_tracker", "handover_tracker"),
        "SiteLayoutPlanner": ("modules.site_layout_planner", "site_layout_planner"),
        "ConstructabilityReviewTool": ("modules.constructability_review_tool", "constructability_review_tool"),
        "ConstructionRiskLog": ("modules.construction_risk_log", "construction_risk_log"),
        "PreTaskPlanningModule": ("modules.pre_task_planning", "pre_task_planning"),
        "ConstructionChangeTracker": ("modules.construction_change_tracker", "construction_change_tracker"),
        "QCInspectionChecklist": ("modules.qc_inspection_checklist", "qc_inspection_checklist"),
        "ConstructionProgressTracker": ("modules.construction_progress_tracker", "construction_progress_tracker"),
        "WeatherImpactTracker": ("modules.weather_impact_tracker", "weather_impact_tracker"),
    },
    "⛽ Reservoir Engineering": {
        "Volumetric Reserves Estimator": ("modules.volumetric_reserves", "run"),
        "Decline Curve Analyzer": ("modules.decline_curve", "run"),
        "Material Balance Calculator": ("modules.material_balance", "run"),
        "Recovery Factor Estimator": ("modules.recovery_factor", "run"),
        "Reservoir Property Calculator": ("modules.reservoir_properties", "run"),
        "Reservoir Flow Simulator": ("modules.reservoir_simulator", "run"),
        "MbalModel": ("modules.mbal_model", "run"),
    },
    "🏗️ Civil and Structural Engineering": {
        "BeamSizeRecommender": ("modules.beam_size_recommender", "beam_size_recommender"),
        "ElevationSketch": ("modules.elevation_sketch", "elevation_sketch"),
        "FoundationSelector": ("modules.foundation_selector", "foundation_selector"),
        "RebarLayoutDesigner": ("modules.rebar_layout_designer", "rebar_layout_designer"),
        "StructuralLoadCalc": ("modules.structural_load_calc", "structural_load_calc"),
        "StructuralLoadCalculator": ("modules.structural_load_calc", "structural_load_calc"),  # alias used in Rev-3
    },
    "💡 Electrical": {
        "CableSizing": ("modules.cable_sizing", "cable_sizing"),
        "PowerDemand": ("modules.power_demand", "run"),
        "VoltageDrop": ("modules.voltage_drop", "voltage_drop"),
        "BreakerSelector": ("modules.breaker_selector", "breaker_selector"),
    },
    "🛡 HSE Management": {
        "RiskAssessmentMatrix": ("modules.risk_assessment_matrix", "run"),
        "JSABuilder": ("modules.jsa_builder", "run"),
        "PermitToWorkTracker": ("modules.permit_to_work_tracker", "run"),
        "IncidentReportTool": ("modules.incident_report_tool", "run"),
        "HSEAuditPlanner": ("modules.hse_audit_planner", "run"),
        "PPEMatrixSelector": ("modules.ppe_matrix_selector", "run"),
        "EmergencyResponsePlan": ("modules.emergency_response_plan", "run"),
        "HSEKPIDashboard": ("modules.hse_kpi_dashboard", "run"),
    },
    "🧾 Quality Management": {
        "DMAICProjectTracker": ("modules.dmaic_project_tracker", "run"),
        "ProcessCapabilityCalculator": ("modules.process_capability_calculator", "run"),
        "RootCauseAnalysisTool": ("modules.root_cause_analysis_tool", "run"),
        "ControlChartGenerator": ("modules.control_chart_generator", "run"),
        "DPMOCalculator": ("modules.dpmo_calculator", "run"),
        "SixSigmaTrainingChecklist": ("modules.six_sigma_training_checklist", "run"),
        "ITPGenerator": ("modules.itp_generator", "run"),
        "NCRTracker": ("modules.ncr_tracker", "run"),
        "QualityAuditChecklist": ("modules.quality_audit_checklist", "run"),
        "MaterialCertificateVerifier": ("modules.material_certificate_verifier", "run"),
        "WeldingNDTTracker": ("modules.welding_ndt_tracker", "run"),
        "LessonsLearnedLog": ("modules.lessons_learned_log", "run"),
        "SupplierQualityScorecard": ("modules.supplier_quality_scorecard", "run"),
        "DocumentControlTracker": ("modules.document_control_tracker", "run"),
    },
    "🎲 Instrumentation": {
        "SensorCalibration": ("modules.sensor_calibration", "sensor_calibration"),
        "LoopCheckRegister": ("modules.loop_check_register", "loop_check_register"),
        "InstrumentSpecSheet": ("modules.instrument_spec_sheet", "instrument_spec_sheet"),
        "IoListGenerator": ("modules.io_list_generator", "io_list_generator"),
        "ControlNarrative": ("modules.control_narrative", "run"),
    },
    "🔬 Simulation": {
        "CompressorEstimator": ("modules.compressor_estimator", "run"),
        "FlashCalc": ("modules.flash_calc", "flash_calc"),
        "MixerSplitter": ("modules.mixer_splitter", "mixer_splitter"),
        "PipeLineSizing": ("modules.pipe_line_sizing", "run"),
        "SeparatorSim": ("modules.separator_sim", "run"),
        "SeparatorSizing": ("modules.separator_sizing", "run"),
        "StreamCalculator": ("modules.stream_calculator", "stream_calculator"),
        "ValveSelector": ("modules.valve_selector", "run"),
        "ValveDrop": ("modules.valve_drop", "run"),
        "PumpSizing": ("modules.pump_sizing", "run"),
        "🧪 Process Flow Simulation": ("modules.process_flow_simulation", "run"),
        "PfdCreator": ("modules.pfd_creator", "run"),
        "PidCreator": ("modules.pid_creator", "run"),
        "BasisOfDesign": ("modules.basis_of_design", "basis_of_design"),
        "HeaterCoolerSim": ("modules.heater_cooler_sim", "run"),
    },
    "🗂️ Interface Management": {
        "InterfaceMatrix": ("modules.interface_matrix", "run"),
        "InterfaceRiskLog": ("modules.interface_risk_log", "interface_risk_log"),
        "InterfaceReview": ("modules.interface_review", "interface_review"),
        "DisciplineOwnership": ("modules.discipline_ownership", "discipline_ownership"),
        "InterdependencyTracker": ("modules.interdependency_tracker", "interdependency_tracker"),
    },
    "🧩 Stakeholder Management": {
        "StakeholderRegister": ("modules.stakeholder_register", "stakeholder_register"),
        "EngagementPlan": ("modules.engagement_plan", "engagement_plan"),
        "FeedbackLog": ("modules.feedback_log", "feedback_log"),
        "CommunicationTracker": ("modules.communication_tracker", "communication_tracker"),
        "InfluenceInterest": ("modules.influence_interest", "influence_interest"),
    },
    "🧾 Procurement Management": {
        "BidEvaluation": ("modules.bid_evaluation", "bid_evaluation"),
        "VendorReview": ("modules.vendor_review", "vendor_review"),
        "SupplierRisk": ("modules.supplier_risk", "supplier_risk"),
        "ProcurementStrategy": ("modules.procurement_strategy", "procurement_strategy"),
        "DeliveryTracker": ("modules.delivery_tracker", "delivery_tracker"),
    },
    "🔍 Risk Management": {
        "Risk": ("modules.risk", "run"),
        "IssueEscalation": ("modules.issue_escalation", "issue_escalation"),
        "BiasChecker": ("modules.bias_checker", "run"),
        "WhatIf": ("modules.what_if", "run"),
    },
    "📅 Planning": {
        "CriticalPath": ("modules.critical_path", "run"),
        "ScheduleDeveloper": ("modules.schedule_developer", "run"),
        "SCurve": ("modules.s_curve", "run"),
        "ProjectTracker": ("modules.project_tracker", "run"),
        "📅 P6 Scheduler": ("modules.p6_scheduler", "run"),
    },
    "📜 Contracts": {
        "ContractAnalyzer": ("modules.contract_analyzer", "run"),
        "ContractsDevelopment": ("modules.contracts_development", "run"),
    },
    "🚀 Agile": {
        "KanbanBoard": ("modules.kanban_board", "run"),
        "SprintPlanner": ("modules.sprint_planner", "run"),
        "StandupNotes": ("modules.standup_notes", "run"),
        "RetrospectiveBoard": ("modules.retrospective_board", "run"),
        "BurndownChart": ("modules.burndown_chart", "burndown_chart"),
    },
    "🏠 Housing / Architecture": {
        "HouseDraftingCanvas": ("modules.house_drafting_canvas", "house_drafting_canvas"),
        "HouseLayoutPlanner": ("modules.house_layout_planner", "run"),
        "RoomSizingEstimator": ("modules.room_sizing_estimator", "room_sizing_estimator"),
        "UtilitiesLayout": ("modules.utilities_layout", "utilities_layout"),
        "SiteReadinessChecklist": ("modules.site_readiness_checklist", "site_readiness_checklist"),
    },
}

def discover_rev3_packages(package_names):
    # Your dynamic discovery logic here
    # For now, just return an empty dict or your actual implementation
    return {}

@st.cache_data(show_spinner=False)
def discover_rev3_packages_cached(package_names):
    return discover_rev3_packages(package_names)
def _qm_lookup_by_module_path(module_path: str):
    """Return (title, func_name) from REV3_GROUPS for a given module_path."""
    for _group_label, entries in REV3_GROUPS.items():
        for title, (mpath, fn) in entries.items():
            if mpath == module_path:
                return title, fn
    return None, None

# 2) Dynamic discovery:
REV3_SCAN_PACKAGES_DEFAULT = ["decisionmate_core", "modules"]
def ensure_rev3_scan_packages():
    if "rev3_scan_packages" not in st.session_state:
        st.session_state.rev3_scan_packages = REV3_SCAN_PACKAGES_DEFAULT[:]



def _refresh_rev3_discovery():
    if "rev3_scan_packages" not in st.session_state:
        st.session_state["rev3_scan_packages"] = []
    found = discover_rev3_packages_cached(st.session_state.rev3_scan_packages)
    return found
    # Merge (seeds win on title collisions so you keep curated nice names)
    for title, pair in found.items():
        REV3_MODULES.setdefault(title, pair)
    st.session_state.rev3_discovered_count = len(found)

# Run once per session by default


# ---------------- Quick Modules (Rev-3 style launcher) ----------------
import importlib

# default packages to scan for legacy tools
DEFAULT_QM_SCAN = ["modules", "decisionmate_core"]

def _find_callable(module_path: str):
    """Import a module and return a sensible entry point callable."""
    mod = importlib.import_module(module_path)
    base = module_path.split(".")[-1]
    for cand in ("run", "main", base):
        fn = getattr(mod, cand, None)
        if callable(fn):
            return fn
    # last chance: first callable at top-level
    for name, obj in vars(mod).items():
        if callable(obj):
            return obj
    raise RuntimeError(f"No callable entry point found in {module_path}")

def _bucket_for(name: str, path: str) -> str:
    """Heuristic categories so it looks like Rev-3 groups."""
    n = f"{name.lower()} {path.lower()}"
    if any(t in n for t in ["reservoir", "mbal", "decline", "volumetric"]): return "⛽ Reservoir"
    if any(t in n for t in ["construction", "concrete", "rebar", "site_", "punch", "handover"]): return "🛠 Construction"
    if any(t in n for t in ["quality", "itp", "ncr", "dpmo", "six_sigma", "audit", "welding"]): return "🧾 Quality"
    if any(t in n for t in ["hse", "permit", "incident", "jsa", "ppe", "emergency"]): return "🛡 HSE"
    if any(t in n for t in ["instrument", "loop", "io_list", "control_narrative"]): return "🎲 Instrumentation"
    if any(t in n for t in ["procurement", "supplier", "vendor", "delivery", "bid", "strategy"]): return "🧾 Procurement"
    if any(t in n for t in ["risk", "bias", "issue_escalation", "what_if"]): return "🔍 Risk"
    if any(t in n for t in ["critical_path", "schedule", "p6", "s_curve", "project_tracker"]): return "📅 Planning"
    if any(t in n for t in ["compressor", "flash", "separator", "mixer", "pump", "pipe", "valve", "heater", "pfd", "pid"]): return "🔬 Simulation"
    if any(t in n for t in ["interface", "interdependency", "discipline_ownership"]): return "🗂 Interface"
    if any(t in n for t in ["stakeholder", "engagement", "communication", "influence_interest", "feedback"]): return "🧩 Stakeholder"
    if any(t in n for t in ["contract", "contracts"]): return "📜 Contracts"
    if any(t in n for t in ["kanban", "sprint", "standup", "retro", "burndown"]): return "🚀 Agile"
    if any(t in n for t in ["house", "room", "layout", "utilities_layout", "elevation"]): return "🏠 Housing / Architecture"
    if any(t in n for t in ["electrical", "voltage", "breaker", "power_demand", "cable"]): return "💡 Electrical"
    if any(t in n for t in ["beam", "foundation", "structural", "rebar", "load"]): return "🏗 Civil / Structural"
    if any(t in n for t in ["financial", "break_even", "cost_estimator"]): return "📊 Business & Finance"
    if any(t in n for t in ["life", "pros_cons", "goal_planner", "rent_vs_buy"]): return "🧠 Personal"
    return "Other"

def _discover_quick_modules():
    # ensure default packages once
    st.session_state.setdefault("rev3_scan_packages", DEFAULT_QM_SCAN)
    # reuse your existing discovery function
    found = discover_rev3_packages_cached(st.session_state.rev3_scan_packages)
    # found: {Nice Title: (module_path, entry_or_guess)}
    # Build categories
    buckets = {}
    for nice_title, (mod_path, _entry) in sorted(found.items()):
        bucket = _bucket_for(nice_title, mod_path)
        buckets.setdefault(bucket, {})[nice_title] = mod_path
    return buckets

def render_quick_modules():
    st.title("⚡ Quick Modules")
    st.caption("All legacy Rev-3 tools, grouped like in Rev-3. (Auto-scanned; no sidebar controls needed.)")

    buckets = _discover_quick_modules()
    if not buckets:
        st.warning("No legacy tools discovered under 'modules' / 'decisionmate_core'.")
        return

    cats = list(buckets.keys())
    cat = st.sidebar.radio("Category", cats, key="qm_cat")
    tools = buckets[cat]
    labels = list(tools.keys())

    sel = st.sidebar.radio("Tool", labels, key="qm_tool")
    st.markdown(f"### {sel}")

    # load + run (with T if accepted)
    try:
        fn = _find_callable(tools[sel])
        # try to call with a translations dict like Rev-3; fall back to no-arg
        try:
            fn({"title": "DecisionMate", "select_module": "Select Module"})
        except TypeError:
            fn()
    except Exception as e:
        st.error(f"Could not open **{sel}** ({tools[sel]}): {e}")
