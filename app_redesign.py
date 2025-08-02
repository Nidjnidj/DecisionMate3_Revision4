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
st.set_page_config(page_title="DecisionMate", layout="wide", page_icon="📊", initial_sidebar_state="expanded")
st.sidebar.image("nijat_logo.png", width=200)

# === Language Selection ===
language = st.sidebar.radio("🌐", ["en", "az", "ru", "tr", "es"], format_func=lambda x: {
    "en": "English",
    "az": "Azərbaycanca",
    "ru": "Русский",
    "tr": "Türkçe",
    "es": "Español"
}.get(x, x), key="language_radio")
T = TRANSLATIONS.get(language, TRANSLATIONS["en"])

def ensure_translation_keys(T):
    fallback = {
        "select_module": "Select Module",
        "login_button": "Login",
        "login_title": "Login",
        "username": "Username",
        "login_warning": "Please enter a username",
        "title": "DecisionMate"
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
from life_career import life_career
from pros_cons import pros_cons
from swot import swot
from rent_vs_buy import rent_vs_buy
from financial_analysis import financial_analysis
from equipment_comparison import equipment_comparison
from what_if import what_if_scenario
from break_even import break_even
from contract_analyzer import contract_analyzer
from contracts_development import contract_development
from schedule_developer import schedule_developer
from kanban_board import kanban_board
from standup_notes import daily_standup
from pump_sizing import pump_selector
from pipe_line_sizing import pipe_sizing
from compressor_estimator import compressor_power
from valve_selector import valve_selector
from pfd_creator import pfd_creator
from pid_creator import pid_creator
from basis_of_design import basis_of_design
from flash_calc import flash_calc
from goal_planner import goal_planner
from heater_cooler_sim import heater_cooler
from knowledge_linker import knowledge_linker
from mixer_splitter import mixer_splitter
from separator_sim import separator_sim
from separator_sizing import separator_sizing
from stream_calculator import stream_calc
from valve_drop import valve_drop_calc

# === Grouped Modules ===
group_modules = {
    "🧐 Personal Decisions": {
        "Life & Career Decisions": life_career,
        "Pros & Cons Evaluator": pros_cons,
        "SWOT Analysis": swot,
        "Goal Planner": goal_planner
    },
    "📊 Business & Financial Tools": {
        "Rent vs Buy Decision": rent_vs_buy,
        "Financial Analysis": financial_analysis,
        "Equipment Comparison": equipment_comparison,
        "What-If Scenario Simulator": what_if_scenario,
        "Break-Even Calculator": break_even
    },
    "🗕️ Planning Tools": {
        "Schedule Developer": schedule_developer
    },
    "📄 Contracts": {
        "Contract Decision Analyzer": contract_analyzer,
        "Contracts Development": contract_development
    },
    "📌 Agile": {
        "Daily Stand-up Notes": daily_standup,
        "Kanban Board": kanban_board
    },
    "🔧 Simulation": {
        "Pump Selector & Sizing": pump_selector,
        "Pipe & Line Sizing Tool": pipe_sizing,
        "Compressor Power Estimator": compressor_power,
        "Valve Type Selector": valve_selector,
        "Process Flow Diagram Creator": pfd_creator,
        "P&ID Diagram Creator": pid_creator,
        "Basis of Design Developer": basis_of_design,
        "Flash Gas Calculator": flash_calc,
        "Heater/Cooler Simulator": heater_cooler,
        "Knowledge Base Linker": knowledge_linker,
        "Mixer & Splitter Tool": mixer_splitter,
        "Separator Simulator": separator_sim,
        "Separator Sizing Tool": separator_sizing,
        "Stream Property Calculator": stream_calc,
        "Valve Pressure Drop Estimator": valve_drop_calc
    },
    "⚙️ Construction": {},
    "🏗️ Civil & Structural": {},
    "⚡ Electrical": {},
    "🎲 Instrumentation": {}
}

# === Module UI ===
st.title(T["title"])
st.sidebar.subheader(T["select_module"])
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
