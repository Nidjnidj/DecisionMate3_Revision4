import streamlit as st
import io
import zipfile
from fpdf import FPDF
from firebase_admin import credentials, initialize_app
import firebase_admin
from firebase_auth import login_user
from firebase_db import log_user_activity
from translations import TRANSLATIONS

# === Firebase Setup ===
if not st.session_state.get("firebase_initialized"):
    cred = credentials.Certificate("serviceAccountKey.json")
    if not firebase_admin._apps:
        initialize_app(cred)
    st.session_state.firebase_initialized = True

# === Page Config ===
st.set_page_config(
    page_title="DecisionMate",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)
st.sidebar.image("nijat_logo.png", width=200)

# === Language Selection ===
language = st.sidebar.radio(
    "🌐", ["en", "az", "ru", "tr", "es"],
    format_func=lambda x: {
        "en": "English",
        "az": "Azərbaycanca",
        "ru": "Русский",
        "tr": "Türkçe",
        "es": "Español"
    }.get(x, x),
    key="language_radio"
)
T = TRANSLATIONS.get(language, TRANSLATIONS["en"])

# === Fallback Translations ===
# === Fallback Translations ===
def ensure_translation_keys(T):
    fallback = {
        "select_module": "Select Module",
        "login_button": "Login",
        "login_title": "Login",
        "username": "Username",
        "login_warning": "Please enter a username",
        "title": "DecisionMate",
        "life_title": "Life & Career Decisions",
        "simple_choices": "Simple Choices",
        "decision_area": "Decision Area",
        "career_change": "Career Change",
        "relocation": "Relocation",
        "further_education": "Further Education",
        "confidence_level": "Confidence Level",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "detailed_scores": "Detailed Scores",
        "importance": "Importance",
        "monthly_rent": "Monthly Rent",
        "property_price": "Property Price",
        "loan_term": "Loan Term (years)",
        "interest_rate": "Interest Rate (%)",
        "monthly_mortgage": "Monthly Mortgage Payment",
        "summary": "Summary",
        "result": "Result",
       "download_pdf": "Download PDF Report",
"heater_cooler_title": "Heater/Cooler Simulation"


    }
    for k, v in fallback.items():
        T.setdefault(k, v)
    return T

T = ensure_translation_keys(T)
# === Authentication ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    with st.sidebar.expander(T["login_title"]):
        username = st.text_input(T["username"], key="username_input")
        login_button = st.button(T["login_button"], key="login_button")
        if username and login_button:
            st.session_state.logged_in = True
            st.session_state.username = username
            log_user_activity(username, "login")
        elif login_button:
            st.warning(T["login_warning"])
            st.stop()

if not st.session_state.get("logged_in"):
    st.stop()

# === Module Imports ===
from modules.interface_matrix import interface_matrix
from modules.life_career import life_career
from modules.pros_cons import run as pros_cons
from modules.goal_planner import run as goal_planner
from modules.risk import run as risk
from modules.bias_checker import run as bias_checker
from modules.swot import swot
from modules.rent_vs_buy import rent_vs_buy
from modules.financial_analysis import financial_analysis
from modules.equipment_comparison import equipment_comparison
from modules.what_if import run as what_if
from modules.break_even import break_even
from modules.contract_analyzer import run as contract_analyzer
from modules.contracts_development import run as contract_development

from modules.critical_path import run as critical_path
from modules.schedule_developer import run as schedule_developer
from modules.s_curve import run as s_curve
from modules.standup_notes import run as standup_notes
from modules.kanban_board import run as kanban_board
from modules.sprint_planner import run as sprint_planner
from modules.retrospective_board import run as retrospective_board
from modules.pump_sizing import run as pump_selector
from modules.pipe_line_sizing import run as pipe_sizing

from modules.power_demand import run as power_demand
from modules.voltage_drop import voltage_drop
from modules.breaker_selector import breaker_selector
from modules.loop_check_register import loop_check_register
from modules.instrument_spec_sheet import instrument_spec_sheet
from modules.io_list_generator import io_list_generator
from modules.compressor_estimator import run as compressor_estimator

from modules.valve_selector import run as valve_selector
from modules.pfd_creator import run as pfd_creator
from modules.pid_creator import run as pid_creator
from modules.basis_of_design import run as basis_of_design
from modules.flash_calc import run as flash_calc
from modules.heater_cooler_sim import run as heater_cooler
from modules.knowledge_linker import run as knowledge_linker
from modules.mixer_splitter import mixer_splitter
from modules.separator_sim import run as separator_sim
from modules.separator_sizing import run as separator_sizing
from modules.stream_calculator import stream_calculator
from modules.house_layout_planner import run as house_layout_planner

from modules.valve_drop import run as valve_drop
from modules.steel_material_tracker import steel_material_tracker
from modules.house_drafting_canvas import house_drafting_canvas
from modules.room_sizing_estimator import room_sizing_estimator
from modules.material_estimator import material_estimator
from modules.utilities_layout import utilities_layout
from modules.elevation_sketch import elevation_sketch
from modules.structural_load_calc import structural_load_calc
from modules.concrete_mix_optimizer import concrete_mix_optimizer
from modules.concrete_pour_log import concrete_pour_log
from modules.beam_size_recommender import beam_size_recommender
from modules.rebar_layout_designer import rebar_layout_designer
from modules.sensor_calibration import sensor_calibration
from modules.interface_risk_log import interface_risk_log
from modules.stakeholder_register import stakeholder_register
from modules.procurement_strategy import procurement_strategy
from modules.cost_estimator import cost_estimator
from modules.work_package_builder import work_package_builder
from modules.foundation_selector import foundation_selector
structural_load_calculator = structural_load_calc
from modules.cable_sizing import cable_sizing
from modules.control_narrative import run as control_narrative
from modules.project_tracker import run as project_tracker
from modules.burndown_chart import burndown_chart
from modules.site_readiness_checklist import site_readiness_checklist



# Interface

from modules.interface_risk_log import interface_risk_log
from modules.discipline_ownership import discipline_ownership
from modules.interdependency_tracker import interdependency_tracker
from modules.interface_review import interface_review
from modules.issue_escalation import issue_escalation

# Stakeholder
from modules.stakeholder_register import stakeholder_register
from modules.engagement_plan import engagement_plan
from modules.influence_interest import influence_interest
from modules.communication_tracker import communication_tracker
from modules.feedback_log import feedback_log

# Procurement
from modules.procurement_strategy import procurement_strategy
from modules.bid_evaluation import bid_evaluation
from modules.supplier_risk import supplier_risk
from modules.delivery_tracker import delivery_tracker
from modules.vendor_review import vendor_review


# === Unified UI Layout ===
st.title(T["title"])
st.sidebar.subheader(T["select_module"])

# === Module Groups ===
group_modules = {
    "🧠 Personal Decisions": {
        "LifeCareer": life_career,
        "ProsCons": pros_cons,
        "GoalPlanner": goal_planner,
        "RentVsBuy": rent_vs_buy
    },
    "📊 Business & Financial": {
        "FinancialAnalysis": financial_analysis,
        "BreakEven": break_even,
        "CostEstimator": cost_estimator
    },
    "🛠️ Construction": {
        "MaterialEstimator": material_estimator,
        "ConcreteMixOptimizer": concrete_mix_optimizer,
        "ConcretePourLog": concrete_pour_log,
        "EquipmentComparison": equipment_comparison,
        "SteelMaterialTracker": steel_material_tracker,
        "WorkPackageBuilder": work_package_builder
    },
    "🏗️ Civil and Structural Engineering": {
        "BeamSizeRecommender": beam_size_recommender,
        "ElevationSketch": elevation_sketch,
        "FoundationSelector": foundation_selector,
        "RebarLayoutDesigner": rebar_layout_designer,
        "StructuralLoadCalc": structural_load_calc,
        "StructuralLoadCalculator": structural_load_calculator
    },
    "💡 Electrical": {
        "CableSizing": cable_sizing,
        "PowerDemand": power_demand,
        "VoltageDrop": voltage_drop,
        "BreakerSelector": breaker_selector
    },
    "🎲 Instrumentation": {
        "SensorCalibration": sensor_calibration,
        "LoopCheckRegister": loop_check_register,
        "InstrumentSpecSheet": instrument_spec_sheet,
        "IoListGenerator": io_list_generator,
        "ControlNarrative": control_narrative
    },
    "🔬 Simulation": {
        "CompressorEstimator": compressor_estimator,
        "FlashCalc": flash_calc,
        "MixerSplitter": mixer_splitter,
        "PipeLineSizing": pipe_sizing,
        "SeparatorSim": separator_sim,
        "SeparatorSizing": separator_sizing,
        "StreamCalculator": stream_calculator,
        "ValveSelector": valve_selector,
        "ValveDrop": valve_drop,
        "PumpSizing": pump_selector,  # ✅ Correct variable name

        "PfdCreator": pfd_creator,
        "PidCreator": pid_creator,
        "BasisOfDesign": basis_of_design,
        "HeaterCoolerSim": heater_cooler,  # ✅ matches the import

    },
    "🗂️ Interface Management": {
        "InterfaceMatrix": interface_matrix,
        "InterfaceRiskLog": interface_risk_log,
        "InterfaceReview": interface_review,
        "DisciplineOwnership": discipline_ownership,
        "InterdependencyTracker": interdependency_tracker
    },
    "🧩 Stakeholder Management": {
        "StakeholderRegister": stakeholder_register,
        "EngagementPlan": engagement_plan,
        "FeedbackLog": feedback_log,
        "CommunicationTracker": communication_tracker,
        "InfluenceInterest": influence_interest
    },
    "🧾 Procurement Management": {
        "BidEvaluation": bid_evaluation,
        "VendorReview": vendor_review,
        "SupplierRisk": supplier_risk,
        "ProcurementStrategy": procurement_strategy,
        "DeliveryTracker": delivery_tracker
    },
    "🔍 Risk Management": {
        "Risk": risk,
        "IssueEscalation": issue_escalation,
        "BiasChecker": bias_checker,
        "WhatIf": what_if
    },
    "📅 Planning": {
        "CriticalPath": critical_path,
        "ScheduleDeveloper": schedule_developer,
        "SCurve": s_curve,
        "ProjectTracker": project_tracker
    },
    "📜 Contracts": {
        "ContractAnalyzer": contract_analyzer,
        "ContractsDevelopment": contract_development

    },
    "🚀 Agile": {
        "KanbanBoard": kanban_board,
        "SprintPlanner": sprint_planner,
        "StandupNotes": standup_notes,
        "RetrospectiveBoard": retrospective_board,
        "BurndownChart": burndown_chart
    },
    "🏠 Housing / Architecture": {
        "HouseDraftingCanvas": house_drafting_canvas,
        "HouseLayoutPlanner": house_layout_planner,
        "RoomSizingEstimator": room_sizing_estimator,
        "UtilitiesLayout": utilities_layout,
        "SiteReadinessChecklist": site_readiness_checklist
    }
}


# === Main Module Selection Logic ===
selected_group = st.sidebar.radio("Module Category", list(group_modules.keys()), key="modern_group")
available_modules = group_modules[selected_group]

if available_modules:
    selected_module = st.sidebar.radio(T["select_module"], list(available_modules.keys()), key="modern_module")
    module_func = available_modules[selected_module]
    key = selected_module.lower().replace(" ", "_")
    if "descriptions" in T and key in T["descriptions"]:
        st.info(T["descriptions"][key])
    try:
        module_func(T)
    except Exception as e:
        st.error(f"❌ Error in module: {e}")
        st.exception(e)
else:
    st.warning("This category has no modules implemented yet.")
