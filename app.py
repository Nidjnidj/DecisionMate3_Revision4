
import streamlit as st
import io
import zipfile
from fpdf import FPDF
from firebase_admin import credentials, initialize_app
import firebase_admin
from firebase_auth import login_user
from firebase_db import log_user_activity
from translations import TRANSLATIONS
import requests
from streamlit_lottie import st_lottie

import requests
import json

@st.cache_data
def load_lottie_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)  # ✅ return dict not str



# === Firebase Setup ===
if not st.session_state.get("firebase_initialized"):
    firebase_config = st.secrets["firebase"]
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(firebase_config))
        initialize_app(cred)
    st.session_state.firebase_initialized = True

# === Page Config ===
st.set_page_config(
    page_title="DecisionMate",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)
# === Global CSS Styling ===
st.markdown("""
<style>
/* 🔵 Global Button Hover Effect */
div.stButton > button:first-child {
    background-color: #0d6efd;
    color: white;
    font-weight: 600;
    border-radius: 8px;
    transition: all 0.3s ease-in-out;
}

div.stButton > button:first-child:hover {
    background-color: #003d99;
    transform: scale(1.04);
}
</style>
""", unsafe_allow_html=True)
# === Module Area Styling ===
st.markdown("""
<style>
.module-card {
    background-color: #f9f9f9;
    padding: 2rem;
    border-radius: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    margin-top: 1.5rem;
}
.module-title {
    font-size: 28px;
    font-weight: 700;
    color: #222;
    margin-bottom: 0.5rem;
}
.module-description {
    font-size: 16px;
    color: #666;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@media screen and (max-width: 768px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .css-1d391kg {
        flex-direction: column !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.sidebar.image("nijat_logo.png", width=150)
# === Center Tagline Section ===

if not st.session_state.get("logged_in", False):
    st.markdown("<div style='text-align: center; margin-top: -20px;'>"
                "<h1 style='font-size: 2.5em;'>🚀 Smarter Decisions. Faster Outcomes.</h1>"
                "<p style='font-size: 1.2em; color: gray;'>Empowering professionals and thinkers to make confident, informed choices.</p>"
                "</div>", unsafe_allow_html=True)

    lottie_decision = load_lottie_file("animations/data_analysis.json")
    st_lottie(lottie_decision, speed=1, loop=True, height=300)



if not st.session_state.get("logged_in", False):
    with st.container():
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown("### 🔧 Why DecisionMate?")
            st.markdown("""
            DecisionMate is your all-in-one decision support platform designed for:

            - 🧠 **Business Analysts & Engineers** – Run NPV, IRR, CAPEX, and What-If scenarios instantly.  
            - 🧭 **Life & Career Planners** – Evaluate personal or professional decisions with structured scoring and SWOT tools.  
            - 🛠️ **Project Managers** – Plan critical paths, break-even points, and compare equipment performance.  
            - 💡 **Thoughtful Individuals** – Make smarter life, work, and financial choices with clarity and confidence.  

            Use it anywhere - no spreadsheets, no complex software, just fast and structured insights.
            """)

            st.markdown("##### ⚡ Instant Calculations")
            st.caption("Run NPV, IRR, CAPEX, OPEX, and break-even in seconds.")

            st.markdown("##### 📊 Visual Insights")
            st.caption("Get radar charts, SWOT matrices, and sensitivity diagrams.")

            st.markdown("##### 🌐 Multilingual & Modular")
            st.caption("Use in EN, AZ, RU, TR, ES — fully modular and scalable.")

            st.markdown("### ✨ Why Users Love DecisionMate")
            st.caption("_Helping professionals worldwide make smarter business, technical, and personal decisions - with clarity and confidence._")

        with col2:
            lottie_team = load_lottie_file("animations/business_team.json")
            st_lottie(lottie_team, height=280)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("🚀 **Instant Calculations**")
        st.caption("Run NPV, IRR, CAPEX, OPEX, and break-even in seconds.")

    with col2:
        st.markdown("📊 **Visual Insights**")
        st.caption("Get radar charts, SWOT matrices, and sensitivity diagrams.")

    with col3:
        st.markdown("🌐 **Multilingual & Modular**")
        st.caption("Use in EN, AZ, RU, TR, ES — fully modular and scalable.")

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
st.sidebar.caption(f"🈯 Language: {language.upper()}")
T = TRANSLATIONS.get(language, TRANSLATIONS["en"])

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
        "save": "Save",
        "load": "Load",
        "save_success": "Project saved successfully!",
        "load_success": "Project loaded successfully!",
        "load_warning": "No data found.",
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


# === Welcome Section ===
# === Better Welcome Section ===
# === Hero Section Style ===
st.markdown("""
<style>
.hero-card {
    background-color: #ffffff;
    padding: 2rem;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    margin-top: 2rem;
    margin-bottom: 2rem;
}
.hero-title {
    font-size: 42px;
    font-weight: 800;
    color: #0d6efd;
    margin-bottom: 0.5rem;
}
.hero-subtitle {
    font-size: 20px;
    color: #555;
    margin-bottom: 0.5rem;
}
.hero-quote {
    font-size: 16px;
    color: #777;
    font-style: italic;
    margin-bottom: 1.5rem;
}
.hero-list li {
    margin-bottom: 0.5rem;
    font-size: 16px;
    color: #333;
}
.footer {
    text-align: center;
    font-size: 14px;
    color: #888;
    margin-top: 4rem;
}
</style>
""", unsafe_allow_html=True)

# === Hero Content ===
if not st.session_state.get("logged_in", False):
    with st.container():
        st.markdown("<div class='hero-card'>", unsafe_allow_html=True)
        col1, col2 = st.columns([1.5, 1])

        with col1:
            st.markdown("<div class='hero-title'>DecisionMate</div>", unsafe_allow_html=True)
            st.markdown("<div class='hero-subtitle'>Smarter Decisions. Faster Outcomes.</div>", unsafe_allow_html=True)
            st.markdown("<div class='hero-quote'>“Make every decision count — in life, work, and beyond.”</div>", unsafe_allow_html=True)

            st.markdown("""
            <ul class='hero-list'>
                <li>📊 <strong>Business Tools:</strong> NPV, IRR, Break-even, What-if</li>
                <li>🧠 <strong>Personal Choices:</strong> Life & Career, Pros & Cons</li>
                <li>🛠 <strong>Engineering Simulations:</strong> Pumps, PFD, Compressors</li>
                <li>🌐 <strong>Languages:</strong> English, AZ, RU, TR, ES</li>
            </ul>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div style='display:flex; align-items:center; height:100%;'>", unsafe_allow_html=True)

            with open("animations/cat_typing.json", "r", encoding="utf-8") as f:
                lottie_cat = json.load(f)

            if lottie_cat:
                st_lottie(lottie_cat, height=240, key="welcome_animation_main")
            else:
                st.image("nijat_logo.png", use_column_width=True)

            st.markdown("</div>", unsafe_allow_html=True)



# === Footer ===
if not st.session_state.get("logged_in", False):
    st.markdown("<div class='footer'>DecisionMate v3.0 | Designed by Nijat Isgandarov | © 2025</div>", unsafe_allow_html=True)



# --- Login / Guest Access Block ---

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "guest" not in st.session_state:
    st.session_state.guest = False

if not st.session_state.logged_in:
    with st.sidebar.expander("🔑 Login to Your Account", expanded=True):
        st.markdown("**Enter your credentials:**")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", key="login_btn"):
            if username and password:
                # Simulate actual validation logic here
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.guest = False
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Please enter both username and password.")

    st.markdown("---")
    st.markdown("### 👇 Or Try Without Login")
    st.markdown("_Explore features as a guest (saving disabled)._")

    if st.button("🚀 Get Started", use_container_width=True, key="get_started_btn"):
        st.session_state.logged_in = True
        st.session_state.username = "Guest"
        st.session_state.guest = True
        st.rerun()

    st.stop()





# === The rest of the code including all imports, group_modules, and UI ===
# Assume all working modules and selectors are integrated exactly as provided earlier.

# === Module Imports ===
from modules.interface_matrix import run as interface_matrix
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


from modules.cost_estimator import cost_estimator
from modules.work_package_builder import work_package_builder
from modules.foundation_selector import foundation_selector
structural_load_calculator = structural_load_calc
from modules.cable_sizing import cable_sizing
from modules.control_narrative import run as control_narrative
from modules.project_tracker import run as project_tracker
from modules.burndown_chart import burndown_chart
from modules.site_readiness_checklist import site_readiness_checklist
from modules.construction_daily_log import construction_daily_log
from modules.manpower_tracker import manpower_tracker
from modules.construction_meeting_notes import construction_meeting_notes



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
from modules.construction_progress_tracker import construction_progress_tracker
from modules.construction_change_tracker import construction_change_tracker
from modules.qc_inspection_checklist import qc_inspection_checklist
from modules.weather_impact_tracker import weather_impact_tracker
from modules.pre_task_planning import pre_task_planning
from modules.equipment_usage_log import equipment_usage_log
from modules.constructability_review_tool import constructability_review_tool
from modules.construction_risk_log import construction_risk_log
from modules.site_layout_planner import site_layout_planner
from modules.punchlist_tracker import punchlist_tracker
from modules.handover_tracker import handover_tracker
from modules.itp_generator import run as itp_generator
from modules.ncr_tracker import run as ncr_tracker
from modules.quality_audit_checklist import run as quality_audit_checklist
from modules.material_certificate_verifier import run as material_certificate_verifier
from modules.welding_ndt_tracker import run as welding_ndt_tracker
from modules.lessons_learned_log import run as lessons_learned_log
from modules.supplier_quality_scorecard import run as supplier_quality_scorecard
from modules.document_control_tracker import run as document_control_tracker
from modules.dmaic_project_tracker import run as dmaic_project_tracker
from modules.process_flow_simulation import run as process_flow_simulation

from modules.process_capability_calculator import run as process_capability_calculator
from modules.root_cause_analysis_tool import run as root_cause_analysis_tool
from modules.control_chart_generator import run as control_chart_generator
from modules.dpmo_calculator import run as dpmo_calculator
from modules.six_sigma_training_checklist import run as six_sigma_training_checklist
from modules.risk_assessment_matrix import run as risk_assessment_matrix
from modules.jsa_builder import run as jsa_builder
from modules.permit_to_work_tracker import run as permit_to_work_tracker
from modules.incident_report_tool import run as incident_report_tool
from modules.hse_audit_planner import run as hse_audit_planner
from modules.ppe_matrix_selector import run as ppe_matrix_selector
from modules.emergency_response_plan import run as emergency_response_plan
from modules.hse_kpi_dashboard import run as hse_kpi_dashboard
from modules.volumetric_reserves import run as volumetric_reserves
from modules.decline_curve import run as decline_curve
from modules.material_balance import run as material_balance
from modules.recovery_factor import run as recovery_factor
from modules.reservoir_properties import run as reservoir_properties
from modules.reservoir_simulator import run as reservoir_simulator
from modules.mbal_model import run as mbal_model
from modules.p6_scheduler import run as p6_scheduler




# === Unified UI Layout ===
st.title(T["title"])
st.sidebar.subheader(T["select_module"])

GT = T.get("group_titles", {})
# === Module Groups ===
group_modules = {
    GT.get("personal", "🧠 Personal Decisions"): {
        "LifeCareer": life_career,
        "ProsCons": pros_cons,
        "GoalPlanner": goal_planner,
        "RentVsBuy": rent_vs_buy
    },
    GT.get("business", "📊 Business & Financial"): {
        "FinancialAnalysis": financial_analysis,
        "BreakEven": break_even,
        "CostEstimator": cost_estimator
    },
GT.get("construction", "🛠️ Construction"): {
    "MaterialEstimator": material_estimator,
    "ConcreteMixOptimizer": concrete_mix_optimizer,
    "ConcretePourLog": concrete_pour_log,
    "EquipmentComparison": equipment_comparison,
    "SteelMaterialTracker": steel_material_tracker,
    "WorkPackageBuilder": work_package_builder,
    "ConstructionDailyLog": construction_daily_log,
    "ManpowerTracker": manpower_tracker,
    "EquipmentUsageLog": equipment_usage_log,
    "ConstructionMeetingNotes": construction_meeting_notes,
    "PunchlistTracker": punchlist_tracker,
    "HandoverTracker": handover_tracker,

    "SiteLayoutPlanner": site_layout_planner,

    "ConstructabilityReviewTool": constructability_review_tool,

    "ConstructionRiskLog": construction_risk_log,

    "PreTaskPlanningModule": pre_task_planning,

    "ConstructionChangeTracker": construction_change_tracker,

    "QCInspectionChecklist": qc_inspection_checklist,

    "ConstructionProgressTracker": construction_progress_tracker,

    "WeatherImpactTracker": weather_impact_tracker

    },
    GT.get("reservoir", "⛽ Reservoir Engineering"): {
    "Volumetric Reserves Estimator": volumetric_reserves,
    "Decline Curve Analyzer": decline_curve,
    "Material Balance Calculator": material_balance,
    "Recovery Factor Estimator": recovery_factor,
    "Reservoir Property Calculator": reservoir_properties,
    "Reservoir Flow Simulator": reservoir_simulator,
    "MbalModel": mbal_model,
    # More modules coming soon
},

    GT.get("civil", "🏗️ Civil and Structural Engineering"): {
        "BeamSizeRecommender": beam_size_recommender,
        "ElevationSketch": elevation_sketch,
        "FoundationSelector": foundation_selector,
        "RebarLayoutDesigner": rebar_layout_designer,
        "StructuralLoadCalc": structural_load_calc,
        "StructuralLoadCalculator": structural_load_calculator
    },
    GT.get("electrical", "💡 Electrical"): {
        "CableSizing": cable_sizing,
        "PowerDemand": power_demand,
        "VoltageDrop": voltage_drop,
        "BreakerSelector": breaker_selector
    },
    GT.get("hse", "🛡 HSE Management"): {
    "RiskAssessmentMatrix": risk_assessment_matrix,
    "JSABuilder": jsa_builder,
    "PermitToWorkTracker": permit_to_work_tracker,
    "IncidentReportTool": incident_report_tool,
    "HSEAuditPlanner": hse_audit_planner,
    "PPEMatrixSelector": ppe_matrix_selector,
    "EmergencyResponsePlan": emergency_response_plan,
    "HSEKPIDashboard": hse_kpi_dashboard
},

    GT.get("quality", "🧾 Quality Management"): {
    "DMAICProjectTracker": dmaic_project_tracker,
    "ProcessCapabilityCalculator": process_capability_calculator,
    "RootCauseAnalysisTool": root_cause_analysis_tool,
    "ControlChartGenerator": control_chart_generator,
    "DPMOCalculator": dpmo_calculator,
    "SixSigmaTrainingChecklist": six_sigma_training_checklist,
    "ITPGenerator": itp_generator,
    "NCRTracker": ncr_tracker,
    "QualityAuditChecklist": quality_audit_checklist,
    "MaterialCertificateVerifier": material_certificate_verifier,
    "WeldingNDTTracker": welding_ndt_tracker,
    "LessonsLearnedLog": lessons_learned_log,
    "SupplierQualityScorecard": supplier_quality_scorecard,
    "DocumentControlTracker": document_control_tracker

},

    GT.get("instrumentation", "🎲 Instrumentation"): {
        "SensorCalibration": sensor_calibration,
        "LoopCheckRegister": loop_check_register,
        "InstrumentSpecSheet": instrument_spec_sheet,
        "IoListGenerator": io_list_generator,
        "ControlNarrative": control_narrative
    },
    GT.get("simulation", "🔬 Simulation"): {
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
        "🧪 Process Flow Simulation": process_flow_simulation,
        "PfdCreator": pfd_creator,
        "PidCreator": pid_creator,
        "BasisOfDesign": basis_of_design,
        "HeaterCoolerSim": heater_cooler,  # ✅ matches the import

    },
    GT.get("interface", "🗂️ Interface Management"): {
        "InterfaceMatrix": interface_matrix,
        "InterfaceRiskLog": interface_risk_log,
        "InterfaceReview": interface_review,
        "DisciplineOwnership": discipline_ownership,
        "InterdependencyTracker": interdependency_tracker
    },
    GT.get("stakeholder", "🧩 Stakeholder Management"): {
        "StakeholderRegister": stakeholder_register,
        "EngagementPlan": engagement_plan,
        "FeedbackLog": feedback_log,
        "CommunicationTracker": communication_tracker,
        "InfluenceInterest": influence_interest
    },
    GT.get("procurement", "🧾 Procurement Management"): {
        "BidEvaluation": bid_evaluation,
        "VendorReview": vendor_review,
        "SupplierRisk": supplier_risk,
        "ProcurementStrategy": procurement_strategy,
        "DeliveryTracker": delivery_tracker
    },
    GT.get("risk", "🔍 Risk Management"): {
        "Risk": risk,
        "IssueEscalation": issue_escalation,
        "BiasChecker": bias_checker,
        "WhatIf": what_if
    },
    GT.get("planning", "📅 Planning"): {
        "CriticalPath": critical_path,
        "ScheduleDeveloper": schedule_developer,
        "SCurve": s_curve,
        "ProjectTracker": project_tracker,
        "📅 P6 Scheduler": p6_scheduler,

    },
    GT.get("contracts", "📜 Contracts"): {
        "ContractAnalyzer": contract_analyzer,
        "ContractsDevelopment": contract_development

    },
    GT.get("agile", "🚀 Agile"): {
        "KanbanBoard": kanban_board,
        "SprintPlanner": sprint_planner,
        "StandupNotes": standup_notes,
        "RetrospectiveBoard": retrospective_board,
        "BurndownChart": burndown_chart
    },
    GT.get("housing", "🏠 Housing / Architecture"): {
        "HouseDraftingCanvas": house_drafting_canvas,
        "HouseLayoutPlanner": house_layout_planner,
        "RoomSizingEstimator": room_sizing_estimator,
        "UtilitiesLayout": utilities_layout,
        "SiteReadinessChecklist": site_readiness_checklist
    }
}


# === Main Module Selection Logic ===
# === Main Module Selection Logic ===
# ✅ Show user info or guest warning
if st.session_state.guest:
    st.warning("🚧 You are browsing in Guest Mode. Login to access saving and syncing features.")
else:
    st.success(f"Welcome, {st.session_state.username}!")

# === Optional status indicator ===
if st.session_state.logged_in:
    if st.session_state.guest:
        st.sidebar.info("👤 Guest Mode")
    else:
        st.sidebar.info(f"👤 Logged in as: {st.session_state.username}")
    if st.sidebar.button("🔒 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.guest = False
        st.rerun()

if st.sidebar.button("🏠 Back to Welcome"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.guest = False
    st.rerun()

# Proceed with module selection
selected_group = st.sidebar.radio("Module Category", list(group_modules.keys()), key="modern_group")
available_modules = group_modules[selected_group]

if available_modules:
    selected_module = st.sidebar.radio(T["select_module"], list(available_modules.keys()), key="modern_module")
    module_func = available_modules[selected_module]
    key = selected_module.lower().replace(" ", "_")

    # Show Module Section
    st.markdown("<div class='module-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='module-title'>{selected_module}</div>", unsafe_allow_html=True)

    if "descriptions" in T and key in T["descriptions"]:
        st.markdown(f"<div class='module-description'>{T['descriptions'][key]}</div>", unsafe_allow_html=True)

    try:
        module_func(T)
    except Exception as e:
        st.error(f"❌ Error in module: {e}")
        st.exception(e)

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("This category has no modules implemented yet.")
if not st.session_state.get("logged_in", False):
    with st.container():
        st.markdown("---")  # horizontal separator
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                with open("animations/cat_typing.json", "r", encoding="utf-8") as f:
                    cat_lottie = json.load(f)
                st_lottie(cat_lottie, height=240, key="cat_typing")
            except FileNotFoundError:
                st.image("nijat_logo.png", use_column_width=True)

