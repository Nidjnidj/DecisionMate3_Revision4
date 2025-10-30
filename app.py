import json, hashlib, time, sys, pathlib
from typing import Dict, Any, Optional, Callable
import importlib.util
import streamlit as st
from services.workspace_openers import open_pm_workspace, open_ops_hub
from services.ui_helpers import artifact_status_label, progress_bar, right_rail_gate, STATUS_COLORS
from services.artifact_helpers import artifact_status_summary, required_artifacts_for_phase
from frontdoor import render_frontdoor  # NEW

# ---- Rev3 dynamic discovery helpers ----
import importlib, pkgutil, inspect, os
import inspect  # for checking a function’s signature
# --- Rev-3 Quick Modules catalog + runner (uses Rev-3 calling convention) ---
import importlib, inspect
# === Pipeline step modules (safe imports) ===
# Services / Data (fallback to local files if 'services'/'data' packages not present)
# --- History (optional) ---
# --- internal services imports (prefer package paths) ---
from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel
# app.py (top-level imports, with your other workflow imports)


from services.history import append_snapshot, get_history
from services.industries import route as industries_route
from services.industry_gate_requirements import list_required_artifacts_industry_aware
from services.rev3_module_launcher import REV3_GROUPS
from services.industry_gate_requirements import (
    list_required_artifacts_industry_aware,
    IT_GATE_CHECK,
    HEALTHCARE_GATE_CHECK,
    GREEN_GATE_CHECK,

    MANUFACTURING_GATE_CHECK,
)
from services.rev3_module_launcher import run_legacy, discover_rev3_packages, discover_rev3_packages_cached
from services import stakeholders as _stake
from services import action_center as _ac  # optional: used for “Create actions”
# --- PM Hub renderers (add this next to the other industry hub imports) ---


from services.industries import route
from services.fel_governance import (
    STAGE_DEFAULT_DELIVERABLES,
    REQUIRED_ARTIFACTS_STAGE,
    ensure_stage_default_deliverables,
)

from services.kpis import render_kpis

try:
    from services.utils import back_to_hub
except Exception:
    from utils import back_to_hub

try:
    from data.firestore import list_projects, create_project, save_project_doc, load_project_doc
except Exception:
    from firestore import list_projects, create_project, save_project_doc, load_project_doc
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # for older Streamlit
        st.experimental_rerun()

def _toggle_nav():
    st.session_state["nav_open"] = not st.session_state.get("nav_open", False)
    _rerun()


# Rev3 core fallbacks
try:
    from decisionmate_core.artifact_service import ArtifactService
except Exception:
    from artifact_service import ArtifactService

try:
    from decisionmate_core.dependencies import PRODUCER
except Exception:
    from dependencies import PRODUCER

import streamlit as st

st.set_page_config(
    page_title="DecisionMate3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide "View source" and GitHub link
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    .viewerBadge_link__qRIco {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# --- Front door gating (run this BEFORE any UI builds) ---
# --- Front door gating (auto-guest; no splash) ---
st.session_state.setdefault("auth_state", "guest")
# (Nothing else here; no render_frontdoor / st.stop)

# Minimal translations dict many Rev-3 tools expect
REV3_T = {
    "title": "DecisionMate",
    "select_module": "Select Module",
    "group_titles": {}  # your modules read T.get("group_titles", {})
}

def _import_legacy_module(module_path: str):
    import importlib.util
    base = module_path.split(".")[-1]
    candidates = [module_path, f"modules.{base}", base, f"decisionmate_core.{base}"]
    last_err = None
    for cand in candidates:
        try:
            if importlib.util.find_spec(cand) is not None:
                return importlib.import_module(cand)
        except Exception as e:
            last_err = e
    # if we get here, import failed for all candidates
    raise last_err or ModuleNotFoundError(f"Cannot import {module_path}")

def run_legacy(module_path: str, func_name: str):
    """Import legacy module and run with Rev-3 calling convention if available."""
    mod = _import_legacy_module(module_path)
    base = mod.__name__.split(".")[-1]
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        for cand in ( "run", "main", base ):
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
REV3_T["group_titles"] = {
    "🧠 Personal Decisions": "Personal Decisions",
    "📊 Business & Financial": "Business & Financial",

    "⛽ Reservoir Engineering": "Reservoir Engineering",
    "🏗️ Civil and Structural Engineering": "Civil & Structural",
    "💡 Electrical": "Electrical",
    "🛡 HSE Management": "HSE",
    "🧾 Quality Management": "Quality",
    "🎲 Instrumentation": "Instrumentation",
    "🔬 Simulation": "Simulation",
    "🗂️ Interface Management": "Interface Management",
    "🧩 Stakeholder Management": "Stakeholder Management",
    "🧾 Procurement Management": "Procurement",
    "🔍 Risk Management": "Risk",
    "📅 Planning": "Planning",
    "📜 Contracts": "Contracts",
    "🚀 Agile": "Agile",
    "🏠 Housing / Architecture": "Housing / Architecture",
}



def _rev3_title_from_mod(name: str) -> str:
    # “foo_bar” -> “Foo Bar”
    return name.split(".")[-1].replace("_", " ").title()

def _try_register_module(index: dict, module_path: str):
    """
    Try to import a module and find a callable entry point.
    Accepted names: run, main, <module_basename>
    """
    try:
        mod = importlib.import_module(module_path)
    except Exception:
        return
    entry = None
    for cand in ("run", "main", module_path.split(".")[-1]):
        fn = getattr(mod, cand, None)
        if callable(fn):
            entry = cand
            break
    if not entry:
        return
    # Optional: reject obviously non-UI libs
    if getattr(mod, "__file__", "").endswith("__init__.py"):
        # Still fine, keep it if it has a callable
        pass
    title = _rev3_title_from_mod(module_path)
        # Skip Ops Hub packages in the Modules catalog
    leaf = module_path.split(".")[-1]
    if leaf.startswith(("ops_", "ops")):
        return

    index[title] = (module_path, entry)

def discover_rev3_packages(package_names: list[str]) -> dict[str, tuple[str, str]]:
    """
    Walk packages and register any module that exposes a callable entry point.
    Returns: {Nice Title: (module_path, entry_name)}
    """
    index: dict[str, tuple[str, str]] = {}
    for pkg_name in package_names:
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue
        pkg_path = os.path.dirname(getattr(pkg, "__file__", "") or "")
        if not pkg_path:
            continue
        # Scan python modules under this package
        for m in pkgutil.walk_packages([pkg_path], prefix=pkg_name + "."):
            name = m.name
            # Skip obvious non-apps
            if any(seg in name for seg in (".tests", ".test", ".fixtures", ".unit_operations")):
                # keep unit_operations for Eng sim only; most are not standalone screens
                continue
            _try_register_module(index, name)
    return index
# Cache the (slow) package scan so the UI feels snappy
@st.cache_data(show_spinner=False)
def discover_rev3_packages_cached(package_names: list[str]) -> dict[str, tuple[str, str]]:
    return discover_rev3_packages(package_names)
# (optional) use a TTL if you edit modules often:
# @st.cache_data(ttl=60, show_spinner=False)

# --- Make sure local package imports work even if launched from IDE/CWD elsewhere
sys.path.insert(0, str(pathlib.Path(__file__).parent.resolve()))

# =============================================================================
# Artifact registry API (local service)
# =============================================================================
from artifact_registry import (
    save_artifact,
    approve_artifact,
    get_latest,
    list_required_artifacts,
    publish_event,
    read_events,
)
# ---------- BEGIN: industry-aware gate requirements ----------
# === IT modules & contracts (robust imports; works with or without a 'modules' package) ===
try:
    from modules.it_pipeline import run as run_it_pipeline
except Exception:
    try:
        from it_pipeline import run as run_it_pipeline
    except Exception:
        # Safe no-op so render_pipeline() doesn't crash if the module isn't present
        run_it_pipeline = lambda: st.info("IT Pipeline module not available.")

try:
    from modules.it_contracts import IT_BUSINESS_CASE, IT_ENGINEERING, IT_SCHEDULE, IT_COST
except Exception:
    try:
        from it_contracts import IT_BUSINESS_CASE, IT_ENGINEERING, IT_SCHEDULE, IT_COST
    except Exception:
        # Fallback to literal types so the app still works end-to-end
        IT_BUSINESS_CASE = "it_business_case"
        IT_ENGINEERING   = "it_engineering_design"
        IT_SCHEDULE      = "it_schedule_plan"
        IT_COST          = "it_cost_model"

# Keep a handle to the original function
_list_required_artifacts_orig = list_required_artifacts







# ---------- END: industry-aware gate requirements ----------

# --- Green Energy required artifacts (used by Gate Check, Swimlane, PM Hub) ---
GREEN_REQUIRED = {
    # keep it minimal; adjust as you grow
    "wind": {
        "FEL1": [
            {"workstream": "Resource",  "type": "Wind_Resource_Profile"},
            {"workstream": "Engineering","type": "Wind_Turbine_Layout"},
            {"workstream": "Engineering","type": "Wind_Energy_Yield"},
            {"workstream": "Schedule",  "type": "WBS"},
            {"workstream": "Schedule",  "type": "Schedule_Network"},
            {"workstream": "Finance",   "type": "Cost_Model"},
            {"workstream": "Risk",      "type": "Risk_Register"},
        ],
        "FEL2": [
            {"workstream": "Engineering","type": "Wind_Turbine_Layout"},
            {"workstream": "Engineering","type": "Wind_Energy_Yield"},
            {"workstream": "Schedule",  "type": "WBS"},
            {"workstream": "Schedule",  "type": "Schedule_Network"},
            {"workstream": "Finance",   "type": "Cost_Model"},
            {"workstream": "Risk",      "type": "Risk_Register"},
        ],
        "FEL3": [
            {"workstream": "Engineering","type": "Wind_Turbine_Layout"},
            {"workstream": "Engineering","type": "Wind_Energy_Yield"},
            {"workstream": "Schedule",  "type": "WBS"},
            {"workstream": "Schedule",  "type": "Schedule_Network"},
            {"workstream": "Finance",   "type": "Cost_Model"},
            {"workstream": "Risk",      "type": "Risk_Register"},
        ],
        "FEL4": [
            {"workstream": "Engineering","type": "Wind_Turbine_Layout"},
            {"workstream": "Engineering","type": "Wind_Energy_Yield"},
            {"workstream": "Schedule",  "type": "WBS"},
            {"workstream": "Schedule",  "type": "Schedule_Network"},
            {"workstream": "Finance",   "type": "Cost_Model"},
            {"workstream": "Risk",      "type": "Risk_Register"},
        ],
    },
    "solar": {
        "FEL1": [
            {"workstream": "Resource",  "type": "Solar_Irradiance_Profile"},
            {"workstream": "Engineering","type": "Solar_Array_Layout"},
            {"workstream": "Engineering","type": "Solar_Energy_Yield"},
            {"workstream": "Schedule",  "type": "WBS"},
            {"workstream": "Schedule",  "type": "Schedule_Network"},
            {"workstream": "Finance",   "type": "Cost_Model"},
            {"workstream": "Risk",      "type": "Risk_Register"},
        ],
        "FEL2": [], "FEL3": [], "FEL4": []
    },
    "hydrogen": {
        "FEL1": [
            {"workstream": "Resource",  "type": "Hydrogen_Demand_Profile"},
            {"workstream": "Engineering","type": "Hydrogen_Process_Package"},
            {"workstream": "Schedule",  "type": "WBS"},
            {"workstream": "Schedule",  "type": "Schedule_Network"},
            {"workstream": "Finance",   "type": "Cost_Model"},
            {"workstream": "Risk",      "type": "Risk_Register"},
        ],
        "FEL2": [], "FEL3": [], "FEL4": []
    }
}

def required_artifacts_for_phase(phase_code: str) -> list[dict]:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "oil_gas"))
    if str(industry) == "green_energy":
        proj_type = str(st.session_state.get("green_project_type", "wind")).lower()
        return GREEN_REQUIRED.get(proj_type, {}).get(phase_code, [])
    # O&G / other industries use whatever the registry says
    return list_required_artifacts_industry_aware(phase_code, industry) or []

# =============================================================================
# Services
# =============================================================================
from services.history import append_snapshot, get_history
# app.py (near the top)
try:
    from config.modules_config import TAXONOMY
except Exception:
# app.py (fallback TAXONOMY)
    from types import SimpleNamespace
    TAXONOMY = SimpleNamespace(
        industries=[
            "oil_gas",
            "green_energy",
            "it",
            "healthcare",
            "government_infrastructure",  # NEW
            "aerospace_defense",          # NEW
            "manufacturing",
            "arch_construction"              # NEW
        ],
        modes=["projects", "ops"],
        fel_stages=["FEL1", "FEL2", "FEL3", "FEL4"],
        ops_modes=["daily_ops", "small_projects", "call_center"],
    )

st.caption(f"Loaded industries: {getattr(TAXONOMY, 'industries', [])}")



try:
    from services.industries import route
except Exception:
    from industries import route

from services.utils import back_to_hub
from data.firestore import list_projects, create_project, save_project_doc, load_project_doc


# ---- View routing (Hub vs Ops Hub vs Modules)
if "view" not in st.session_state:
    st.session_state["view"] = "Workspace"  # default landing

SHOW_PM_HUB = True  # keep PM Hub visible by default

def _locked_group():
    """
    Returns:
      'projects' if a PM project is active,
      'ops'      if an Ops project is active,
      None       if nothing is locked.
    """
    ns = st.session_state.get("active_namespace") or ""
    if ":projects" in ns:
        return "projects"
    if ":ops:" in ns:
        return "ops"
    return None

def _nav_items_for_mode():
    """Hide tabs that shouldn't be reachable while locked."""
    lock = _locked_group()
    if lock == "projects":
        # PM project active → hide Ops Hub
        base = ["Workspace", "Modules", "Quick Modules", "AI Services"]
        return (["PM Hub"] + base) if SHOW_PM_HUB else base
    if lock == "ops":
        # Ops project active → hide PM screens
        return ["Ops Hub", "Modules", "Quick Modules", "AI Services"]
    # Unlocked
    base = ["Ops Hub", "Workspace", "Modules", "Quick Modules", "AI Services"]
    return (["PM Hub"] + base) if SHOW_PM_HUB else base

def _mode_from_view(view: str) -> str:
    """Mode follows lock if present; otherwise derived from view."""
    lock = _locked_group()
    if lock:
        return lock
    return "ops" if view == "Ops Hub" else "projects"
# --- Fast Start helper: ensure there is an active project ---
def _ensure_default_project(mode: str = "projects"):
    username = st.session_state.get("username", "Guest")
    industry = st.session_state.get("industry", "oil_gas")
    ns = f"{industry}:projects" if mode == "projects" else f"{industry}:ops:{st.session_state.get('ops_mode','daily_ops')}"

    if not st.session_state.get("active_project_id") or st.session_state.get("active_namespace") != ns:
        try:
            existing = list_projects(username, ns) or {}
        except Exception:
            existing = {}
        if existing:
            # open the first project found
            pid = sorted(existing.keys())[0]
        else:
            # create a new one silently
            pid = create_project(username, ns, "My First Project")
            try:
                save_project_doc(username, ns, pid, "meta", {"industry": industry, "created_by": username})
            except Exception:
                pass
        st.session_state.active_project_id = pid
        st.session_state.active_namespace = ns
        st.session_state.project_industry = industry
NAV_ITEMS = _nav_items_for_mode()
# Fast-start: auto-provision a project for the current group
_ensure_default_project(_mode_from_view(st.session_state.get("view","PM Hub")))


# keep current view if it still exists, else default to the first item
current = st.session_state.get("view") or NAV_ITEMS[0]
if current not in NAV_ITEMS:
    st.session_state["view"] = NAV_ITEMS[0]
    current = NAV_ITEMS[0]

_choice = st.sidebar.radio(
    "Navigate",
    NAV_ITEMS,
    index=NAV_ITEMS.index(current),
    key="nav_radio"
)
if _choice != st.session_state["view"]:
    st.session_state["view"] = _choice
    try:
        st.rerun()
    except Exception:
        _rerun()

# Inline navigation fallback (shows in main area if sidebar is collapsed)
try:
    nav_items_now = _nav_items_for_mode()
    if st.session_state.get("view") not in nav_items_now:
        st.session_state["view"] = nav_items_now[0]
    st.markdown("<div class='dm-card'>", unsafe_allow_html=True)
    st.markdown("#### Navigation (inline fallback)", unsafe_allow_html=True)
    _choice_inline = st.radio(
        "Navigate",
        nav_items_now,
        index=nav_items_now.index(st.session_state["view"]),
        key="nav_radio_inline"
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if _choice_inline != st.session_state["view"]:
        st.session_state["view"] = _choice_inline
        _rerun()
except Exception:
    pass

# after:
# _choice = st.sidebar.radio(...)



# === Module view router (needed for go_to_module) ===
if st.session_state.get("active_view") == "module":
    import importlib, inspect, streamlit as st

    info = st.session_state.get("module_info") or {}
    module_path = info.get("module_path")
    entry = info.get("entry") or "render"
    context = info.get("context") or {}

    if not module_path:
        st.error("No module specified.")
        st.stop()

    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        st.error(f"Failed to import module '{module_path}': {e}")
        st.stop()

    fn = getattr(mod, entry, None) or getattr(mod, "render", None) or getattr(mod, "run", None)
    if not callable(fn):
        st.error(f"Module '{module_path}' has no callable entry ('{entry}', 'render', or 'run').")
        st.stop()

    # Call with only the kwargs the function accepts
    try:
        params = set(inspect.signature(fn).parameters.keys())
    except Exception:
        params = set()

    kwargs = {}
    if "T" in params: kwargs["T"] = REV3_T  # many Rev3 tools accept T
    if "st" in params: kwargs["st"] = st
    # pass through any context keys the tool declares
    for k in ("industry", "submode", "mode"):
        if k in params and k in context:
            kwargs[k] = context[k]

    fn(**kwargs) if kwargs else fn()
    st.stop()
# === PM Hub router (needed when buttons set active_view="pm_hub") ===
# --- PM Hub router ---
if st.session_state.get("active_view") == "pm_hub":
    ind = (
        st.session_state.get("pm_hub_industry")
        or st.session_state.get("project_industry")
        or st.session_state.get("industry")
        or ""
    ).lower()

    try:
        if ind == "oil_gas":
            from workflows import pm_hub_oil_gas as pmo
            pmo.render(); st.stop()


        elif ind == "manufacturing":
            from workflows import pm_hub_manufacturing as pmm
            pmm.render(); st.stop()

        elif ind == "healthcare":
            from workflows import pm_hub_healthcare as pmh
            pmh.render(); st.stop()

        elif ind == "aerospace_defense":
            from workflows import pm_hub_aerospace_defense as pma
            pma.render(); st.stop()

        elif ind == "government_infrastructure":
            from workflows import pm_hub_government_infrastructure as pmg
            pmg.render(); st.stop()

        elif ind == "it":
            from workflows import pm_hub_it as pmit
            pmit.render(); st.stop()

        elif ind in ("green", "green_energy"):
            from workflows import pm_hub_green_energy as pmge
            pmge.render(); st.stop()

        elif ind in ("arch_construction", "architecture_construction"):
            from workflows import pm_hub_arch_construction as pmac
            _call_pm_hub_render(pmac); st.stop()


        else:
            st.warning(f"No PM Hub registered for industry '{ind}'.")

    except Exception as e:
        st.error(f"Failed to open PM Hub for '{ind}': {e}")

    st.stop()
# --- tiny helpers used by Ops & requirements ---
def _safe_rerun():
    rr = getattr(st, "rerun", None)
    if callable(rr):
        rr()
    else:
        rr_old = getattr(st, "experimental_rerun", None)
        if callable(rr_old):
            rr_old()

def _ops_day_phase_id(date_str: str | None = None) -> str:
    """Use a day-based phase id so all daily Ops artifacts group naturally."""
    import datetime as _dt
    d = date_str or _dt.date.today().isoformat()
    return f"DAY-{d}"
# --- simple in-memory Ops projects (per session) ---
def _ops_projects():
    return st.session_state.setdefault("_ops_projects", {})

def _ops_save_project(pid: str, name: str, industry: str):
    _ops_projects()[pid] = {"name": name, "industry": industry}

def _ops_slug(name: str) -> str:
    import re, time
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(name)).strip("-").lower() or f"ops-{int(time.time())}"
    return f"OPS-{s}"

def _ops_lock(pid: str, industry: str):
    st.session_state["mode"] = "ops"
    st.session_state["active_project_id"] = pid
    st.session_state["current_project_id"] = pid
    st.session_state["project_industry"] = industry
    st.session_state["industry"] = industry
    st.session_state["active_namespace"] = f"{industry}:ops:{pid}"
    # day phase
    st.session_state["current_phase_id"] = _ops_day_phase_id()

def render_requirements(industry: str, phase_code: str, proj_type: str = None):
    st.markdown("### Required Artifacts for Phase")

# Use Ops mapping for OPS_* phases; otherwise use industry-aware project mapping
    try:
        from artifact_registry import list_required_artifacts as _list_req
    except Exception:
        _list_req = lambda code: []

    if str(phase_code).startswith("OPS_"):
        reqs = _list_req(phase_code) or []
    else:
        reqs = list_required_artifacts_industry_aware(phase_code, industry) or []

    if not reqs:
        st.caption("No requirements registered for this phase.")
        return

    project_id = st.session_state.get("current_project_id", "P-DEMO")
    phase_id   = st.session_state.get("current_phase_id",  f"PH-{phase_code}")

    cols = st.columns(2)
    done = 0
    for i, r in enumerate(reqs):
        ws, typ = r.get("workstream","?"), r.get("type","?")
        rec = get_latest(project_id, typ, phase_id) if get_latest else None
        status = (rec or {}).get("status", "Missing")
        is_ok  = status == "Approved"
        if is_ok: done += 1

        with cols[i % 2]:
            badge = "✅ Approved" if is_ok else ("⏳ Pending" if status=="Pending" else "✖️ Missing")
            st.write(f"**{ws} → {typ}**: {badge}")

            if rec and status == "Pending" and approve_artifact:
                if st.button(f"Approve {typ}", key=f"approve_{typ}_{i}"):
                    approve_artifact(project_id, rec["artifact_id"])
                    _safe_rerun()

            if not rec and save_artifact:
                if st.button(f"Save {typ} (Draft)", key=f"draft_{typ}_{i}"):
                    save_artifact(project_id, phase_id, ws, typ, {"auto": True}, status="Draft")
                    _safe_rerun()

    st.caption(f"Progress: {done}/{len(reqs)} approved")
# --- lightweight event loop (works with artifact_registry.read_events) ---
_EVENT_HANDLERS = st.session_state.setdefault("_event_handlers", {})

def register_handler(event_type: str, fn):
    """Optional: call register_handler('artifact.approved', fn) elsewhere to react to events."""
    _EVENT_HANDLERS.setdefault(event_type, []).append(fn)

def drain_events(project_id: str):
    """Fetch recent events and dispatch to any registered handlers (safe no-ops if none)."""
    try:
        from artifact_registry import read_events  # uses in-memory fallback when no Firestore
    except Exception:
        read_events = None
    if not read_events:
        return

    last_ts = int(st.session_state.get("_last_event_ts", 0))
    evts = read_events(project_id) or []

    # process in chronological order and skip already-seen
    for e in sorted(evts, key=lambda x: int(x.get("ts", 0))):
        ts = int(e.get("ts", 0))
        if ts <= last_ts:
            continue
        for fn in _EVENT_HANDLERS.get(e.get("event_type", ""), []):
            try:
                fn(e)
            except Exception:
                pass  # keep UI resilient
        st.session_state["_last_event_ts"] = ts

# === Ops Hub router (daily_ops, small_projects, call_center) ===
import importlib
# --- discover industries from workflows so lists never go stale ---
import pkgutil

def _discover_industries_from_workflows() -> set[str]:
    found = set()
    try:
        import workflows
        for m in pkgutil.iter_modules(workflows.__path__):
            name = m.name
            if name.startswith("pm_hub_"):
                found.add(name[len("pm_hub_"):])
            if name.startswith("ops_hub_"):
                found.add(name[len("ops_hub_"):])
    except Exception:
        pass
    return found

def _industry_choices() -> list[str]:
    base = list(getattr(TAXONOMY, "industries", [
        "oil_gas","green_energy","it","healthcare",
        "government_infrastructure","aerospace_defense",
        "manufacturing","arch_construction",
    ]))
    discovered = _discover_industries_from_workflows()
    return sorted(set(base) | discovered)
# ---- local tolerant router for Ops Hub (supports call_center fallback) ----
import importlib

def _render_ops_hub(industry: str, ops_mode: str) -> bool:
    """
    Try to render workflows.ops_hub_{industry}.render(...).
    If ops_mode == 'call_center' and the industry hub doesn't handle it,
    fall back to ops_call_center.render(...).
    Returns True if something rendered, else False.
    """
    slug = industry.lower().strip()

    # 1) Try industry-specific Ops Hub
    try:
        mod = importlib.import_module(f"workflows.ops_hub_{slug}")
        if hasattr(mod, "render"):
            try:
                mod.render({"ops_mode": ops_mode, "industry": slug})
            except TypeError:
                mod.render(industry=slug, submode=ops_mode)
            return True
    except Exception:
        pass  # we'll try fallback below

    # 2) Fallback for Call Center
    if ops_mode == "call_center":
        try:
            cc = importlib.import_module("ops_call_center")
            if hasattr(cc, "render"):
                try:
                    cc.render({"industry": slug})
                except TypeError:
                    cc.render(industry=slug)
                return True
        except Exception:
            pass

    return False



# === Ops Hub view (clean, single-pass; no unreachable code) ===
if st.session_state.get("view") == "Ops Hub":
    with st.sidebar:
        st.markdown("### Context")

        # Industry selector (keeps state aligned)
        ops_ind_choices = _industry_choices()
        ops_ind_default = (
            ops_ind_choices.index(st.session_state.get("project_industry", "oil_gas"))
            if st.session_state.get("project_industry") in ops_ind_choices else 0
        )
        ops_ind = st.selectbox(
            "Ops Industry",
            ops_ind_choices,
            index=ops_ind_default,
            key="ops_industry_select",
        )
        st.session_state["industry"] = ops_ind
        st.session_state["project_industry"] = ops_ind

        st.markdown("### Mode")
        ops_mode = st.radio(
            "Sub-mode",
            getattr(TAXONOMY, "ops_modes", ["daily_ops", "small_projects", "call_center"]),
            key="ops_mode",
            horizontal=True,
        )

        st.markdown("### Projects")
        new_ops_name = st.text_input("New Daily Ops project name", key="new_ops_proj_name")
        if st.button("Create Ops Project", use_container_width=True, key="btn_create_ops_proj"):
            name = new_ops_name.strip() or f"Daily Ops {int(time.time())}"
            pid = _ops_slug(name)
            _ops_save_project(pid, name, ops_ind)
            _ops_lock(pid, ops_ind)
            _safe_rerun()

        proj_ids = list(_ops_projects().keys())
        sel = st.selectbox("Select project", ["— none —"] + proj_ids, key="ops_pick_project")
        if sel != "— none —":
            _ops_lock(sel, _ops_projects()[sel]["industry"])

        if st.button("Reset (unlock)", key="ops_reset"):
            for k in ("active_namespace", "active_project_id", "current_project_id", "current_phase_id"):
                st.session_state.pop(k, None)
            _safe_rerun()

    # === Ensure IDs even if no project selected ===
    PHASE_CODE = "OPS_DAILY"
    industry = (st.session_state.get("project_industry", ops_ind) or "oil_gas").lower()
    st.session_state.setdefault("current_project_id", "OPS-DEMO")
    st.session_state.setdefault("current_phase_id", _ops_day_phase_id())

    # === Try to render the industry-specific Ops Hub ===
    rendered = _render_ops_hub(industry, st.session_state.get("ops_mode", "daily_ops"))

    # === Fallback: generic requirements for OPS_DAILY ===
    if not rendered:
        st.info("Showing generic Ops requirements (no industry-specific module found or module errored).")
        render_requirements(industry, PHASE_CODE)

        # (Optional) tiny demo actions
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Seed Well Plan (Draft)", key="ops_seed_wp"):
                save_artifact(st.session_state["current_project_id"], st.session_state["current_phase_id"],
                              "Subsurface", "Well_Plan", {"auto": True}, status="Draft")
                _safe_rerun()
        with c2:
            if st.button("Approve Latest Well Plan", key="ops_approve_wp"):
                rec = get_latest(st.session_state["current_project_id"], "Well_Plan", st.session_state["current_phase_id"])
                if rec:
                    approve_artifact(st.session_state["current_project_id"], rec["artifact_id"])
                    _safe_rerun()

    # Dispatch any events and stop the page so the rest doesn't double-render
    drain_events(st.session_state["current_project_id"])
    st.stop()




# =============================================================================
# Modules registry (new discipline modules) — robust import with fallback
# =============================================================================
# =============================================================================
# Modules registry (new discipline modules) — robust import with fallback
# =============================================================================
try:
    from modules import REGISTRY  # must define a dict like {"Subsurface": callable, ...}
    MODULES_IMPORT_ERROR = None
except Exception as exc:
    MODULES_IMPORT_ERROR = f"Modules package not found or REGISTRY missing: {exc}"

    def _missing(stage: str):
        # generic, no external variable capture
        st.error(MODULES_IMPORT_ERROR or "Modules package not available.")

    REGISTRY = {
        "Subsurface": _missing,
        "Engineering": _missing,
        "Cost": _missing,
        "Schedule": _missing,
        "Risk": _missing,
    }

# =============================================================================
# Optional Firebase init (falls back to in-memory if not configured)
# =============================================================================
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as _fs
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
except Exception:
    # No firebase secrets / SDK → artifact_registry uses in-memory fallback
    pass

# =============================================================================
# Cascade mode: "manual" | "assist" | "auto"
#   manual  -> upstream approvals do NOT create downstream work automatically
#   assist  -> upstream approvals create Pending shells (work requests)
#   auto    -> demo mode; downstream artifacts are created Approved
# =============================================================================
CASCADE_MODE = "manual"

# =============================================================================
# Event Bus (in-app)
# =============================================================================
EVENT_HANDLERS: Dict[str, Callable[[dict], None]] = {}
if "_processed_events" not in st.session_state:
    st.session_state["_processed_events"] = set()

def register_handler(event_type: str, fn: Callable[[dict], None]):
    EVENT_HANDLERS[event_type] = fn

def process_events(project_id: str):
    """Pull recent events from registry and dispatch unseen ones."""
    events = read_events(project_id)  # latest first
    for e in events:
        key = f"{e.get('ts')}::{e.get('event_type')}::{e.get('payload',{}).get('artifact_id','_')}"
        if key in st.session_state["_processed_events"]:
            continue
        handler = EVENT_HANDLERS.get(e.get("event_type"))
        if handler:
            try:
                handler(e)
            except Exception as ex:
                st.warning(f"Handler error for {e.get('event_type')}: {ex}")
        st.session_state["_processed_events"].add(key)

def drain_events(project_id: str, max_iters: int = 5):
    """Process events repeatedly so cascaded events are handled in the same run."""
    for _ in range(max_iters):
        before = len(st.session_state["_processed_events"])
        process_events(project_id)
        after = len(st.session_state["_processed_events"])
        if after == before:
            break

# =============================================================================
# UI chips & helpers
# =============================================================================

CHIP_CSS = """
<style>
.dm-chip { display:inline-flex; align-items:center; gap:.5rem; padding:.35rem .6rem; border-radius:999px; font-size:0.85rem; margin:.25rem; border:1px solid rgba(0,0,0,.08); }
.dm-chip .dot { width:.6rem; height:.6rem; border-radius:50%; display:inline-block; }
.dm-swimlane { display:flex; flex-direction:column; gap:.5rem; }
.dm-row { display:flex; flex-wrap:wrap; align-items:center; gap:.25rem; }
.dm-row h4 { margin: .25rem 0 .25rem 0; }
</style>
"""
st.markdown(CHIP_CSS, unsafe_allow_html=True)

def _initial_status():
    return "Approved" if CASCADE_MODE == "auto" else "Pending"
# --- add this helper somewhere near your other small UI helpers ---

# === Quick Demo — Construction (safe, no writes to widget key) ===
from datetime import datetime
import streamlit as st



# =============================================================================
# Minimal Writers / Simulators (kept for “assist/auto” demo if ever used)
# =============================================================================
def simulate_process_flow(project_id: str, phase_id: str, sources: list):
    save_artifact(project_id, phase_id, "Engineering", "PFD_Package", {
        "pfd_svg_ref": "pfd_demo.svg",
        "stream_table": [{"id": "S1", "T": 60, "P": 10, "phase": "L", "flow_mass": 100.0}],
    }, status=_initial_status(), sources=sources)
    save_artifact(project_id, phase_id, "Engineering", "Equipment_List", {
        "items": [
            {"tag": "P-101", "type": "Pump", "duty": 100, "qty": 2, "est_cost": 75000, "lead_weeks": 16},
            {"tag": "HX-201", "type": "Exchanger", "duty": 500, "qty": 1, "est_cost": 120000, "lead_weeks": 22},
        ]
    }, status=_initial_status(), sources=sources)
    save_artifact(project_id, phase_id, "Engineering", "Utilities_Load", {
        "power_demand_profile": [120, 125, 130],
        "steam_cold_duty": 1.2, "fuel_gas": 0.3,
        "cooling_water": 15.0, "instrument_air": 5.0,
    }, status=_initial_status(), sources=sources)

def seed_schedule_from_engineering(project_id: str, phase_id: str, sources: list):
    save_artifact(project_id, phase_id, "Schedule", "WBS", {
        "nodes": [
            {"id": "1", "parent": None, "name": "Project", "type": "Project", "phase": "FEL", "owner": "PM"},
            {"id": "1.1", "parent": "1", "name": "Procurement", "type": "WP", "phase": "FEL", "owner": "SCM"},
            {"id": "1.2", "parent": "1", "name": "Construction", "type": "WP", "phase": "FEL", "owner": "Construction"},
        ]
    }, status=_initial_status(), sources=sources)
    save_artifact(project_id, phase_id, "Schedule", "Schedule_Network", {
        "activities": [
            {"id": "A1", "name": "Order Pumps", "wbs_id": "1.1", "dur_days": 30, "predecessors": []},
            {"id": "A2", "name": "Install Pumps", "wbs_id": "1.2", "dur_days": 15, "predecessors": ["A1"]},
        ],
        "critical_path_ids": ["A1", "A2"],
        "start_date": "2026-01-01", "finish_date": "2026-02-15"
    }, status=_initial_status(), sources=sources)

# --- Construction logic removed ---
# If you need a placeholder for future industries, you can use:

# =============================================================================
# Event Handlers — human-in-the-loop aware
# =============================================================================
def on_artifact_approved(event: dict):
    # In manual mode, upstream approvals do not auto-request downstream work
    if CASCADE_MODE == "manual":
        return

    payload = event.get("payload", {})
    a_type = payload.get("type")
    phase_id = payload.get("phase_id")
    project_id = event.get("project_id")
    src = [f"{payload.get('artifact_id')}@approved"]

    # NEW: Subsurface → Engineering seed
    if a_type == "Reservoir_Profiles":
        simulate_process_flow(project_id, phase_id, src)

    # Engineering → Schedule seed
    if a_type in (
        "Reference_Case_Identification",
        "Concept_Selected",
        "Defined_Concept",
        "Execution_Concept",
        "PFD_Package",
        "Equipment_List",
        "Utilities_Load",
    ):
        seed_schedule_from_engineering(project_id, phase_id, src)

    # Schedule → Cost seed
    if a_type == "Schedule_Network":
        generate_cost_from_schedule(project_id, phase_id, src)

def _seed_schedule_from_eng_now():
    project_id = st.session_state.get("current_project_id","P-DEMO")
    phase_id   = st.session_state.get("current_phase_id","PH-FEL1")
    seed_schedule_from_engineering(project_id, phase_id, ["Engineering@approved"])

def _seed_cost_from_schedule_now():
    project_id = st.session_state.get("current_project_id","P-DEMO")
    phase_id   = st.session_state.get("current_phase_id","PH-FEL1")
    generate_cost_from_schedule(project_id, phase_id, ["Schedule_Network@approved"])


# -------- Call Center Ops: events --------
def on_ticket_closed(e: dict):
    """Lightweight sampler: 1 in 5 closed tickets → create a Pending QA_Scorecard."""
    import random
    p = e.get("payload", {})
    project_id = e.get("project_id") or st.session_state.get("current_project_id","P-DEMO")
    phase_id = _ops_day_phase_id()
    # bias sampler: always sample P1/P2 by priority text if present
    priority = str(p.get("priority","")).upper()
    force = priority in ("P1","P2","CRITICAL")
    if force or random.randint(1,5) == 1:
        save_artifact(project_id, phase_id, "Quality", "QA_Scorecard", {
            "date_utc": p.get("closed_at"),
            "ticket_id": p.get("ticket_id"),
            "agent_id": p.get("agent_id"),
            "dimensions": [
                {"name":"Process Adherence","weight":0.3,"score":0},
                {"name":"Accuracy","weight":0.4,"score":0},
                {"name":"Soft Skills","weight":0.3,"score":0},
            ],
            "pass_threshold": 80,
        }, status="Pending")

def on_qa_scored(e: dict):
    """If a QA score fails → open a Coaching_Plan (Pending)."""
    p = e.get("payload", {})
    if p.get("pass") is True:
        return
    project_id = e.get("project_id") or st.session_state.get("current_project_id","P-DEMO")
    phase_id = _ops_day_phase_id()
    save_artifact(project_id, phase_id, "Quality", "Coaching_Plan", {
        "agent_id": p.get("agent_id"),
        "trigger": "QA_FAIL",
        "root_cause": "",
        "actions": [
            {"action":"Listen to 3 calls and note gaps","owner":p.get("agent_id"),"due_date":"","done":False},
            {"action":"Shadow top performer for 30 mins","owner":p.get("agent_id"),"due_date":"","done":False},
        ],
    }, status="Pending")

def on_shift_ended(e: dict):
    """Prefill a Shift_Handover (End) from what we already know; supervisor approves."""
    project_id = e.get("project_id") or st.session_state.get("current_project_id","P-DEMO")
    phase_id = _ops_day_phase_id()
    sid = (e.get("payload",{}) or {}).get("shift_id", "")
    # Minimal shell; let module fill details in UI
    save_artifact(project_id, phase_id, "Ops", "Shift_Handover", {
        "shift_id": sid, "type": "End", "checklist": [], "notes": "", "top_issues": []
    }, status="Pending")

def on_daily_rollup(e: dict):
    """Drop a KPI_Snapshot (Pending) – the module can compute/approve."""
    project_id = e.get("project_id") or st.session_state.get("current_project_id","P-DEMO")
    phase_id = _ops_day_phase_id(e.get("payload",{}).get("date"))
    save_artifact(project_id, phase_id, "PMO", "KPI_Snapshot", {
        "date_utc": e.get("payload",{}).get("date"),
        "window": "day",
        "tot_contacts": 0, "answered_in_sla_pct": None, "aht_sec": None, "fcr_pct": None,
        "abandon_pct": None, "qa_pass_pct": None, "backlog": None,
        "notes": "Pending supervisor review"
    }, status="Pending")
register_handler("TICKET_CLOSED", on_ticket_closed)
register_handler("QA_SCORED", on_qa_scored)
register_handler("SHIFT_ENDED", on_shift_ended)
register_handler("DAILY_ROLLUP", on_daily_rollup)

# =============================================================================
# Swimlane & Gate
# =============================================================================
def render_swimlane(project_id: str, phase_code: str, phase_id: str):
    required = required_artifacts_for_phase(phase_code)

    if not required:
        st.info("No required artifacts configured for this phase yet.")
        return
    by_ws: Dict[str, list] = {}
    for r in required:
        by_ws.setdefault(r["workstream"], []).append(r["type"])

    st.markdown("### Phase Swimlane")
    for ws, types in by_ws.items():
        st.markdown(f"#### {ws}")
        st.write("<div class='dm-row'>", unsafe_allow_html=True)
        for t in types:
            latest = get_latest(project_id, t, phase_id)
            status = artifact_status_label(latest)
            color = STATUS_COLORS.get(status, "#9AA0A6")
            chip = f"<span class='dm-chip'><span class='dot' style='background:{color}'></span>{t} — {status}</span>"
            st.write(chip, unsafe_allow_html=True)
        st.write("</div>", unsafe_allow_html=True)

def check_gate_ready(project_id: str, phase_code: str, phase_id: str) -> dict:
    """Return {ready: bool, missing: [..], drafts: [..]}"""
    req = required_artifacts_for_phase(phase_code)

    missing, drafts = [], []
    for r in req:
        latest = get_latest(project_id, r["type"], phase_id)
        if not latest:
            missing.append(f"{r['workstream']} — {r['type']}")
        elif latest.get("status") != "Approved":
            drafts.append(f"{r['workstream']} — {r['type']} (status: {latest.get('status')})")
    ready = (len(missing) == 0 and len(drafts) == 0)
    return {"ready": ready, "missing": missing, "drafts": drafts}
def _ge_config(industry: str, proj_type: str | None):
    """
    Returns:
      resource_art, step_labels (5 items), show_well_plan (bool)
    """
    ind = (industry or "").lower()

    # Industries without subsurface/well planning
    NO_SUBSURFACE = {
        "government_infrastructure",
        "aerospace_defense",
        "manufacturing",

    }
    if ind in NO_SUBSURFACE:
        return {
            "resource_art": None,
            "step_labels": ["1) Not Applicable", "2) Not Applicable", "3) Engineering", "4) Schedule", "5) Cost/Economics"],
            "show_well_plan": False,
        }
    if ind == "manufacturing":
        return {
            "resource_art": None,
            "step_labels": [
                "FEL1 — Screening",
                "FEL2 — Pre-FEED (Concept)",
                "FEL3 — FEED (Definition)",
                "FEL4 — Execution & Detail Design",
            ],
            "show_well_plan": False,
        }


    if ind in NO_SUBSURFACE:
        return {
            "resource_art": None,
            "step_labels": ["1) Not Applicable", "2) Not Applicable", "3) Engineering", "4) Schedule", "5) Cost/Economics"],
            "show_well_plan": False,
        }

    # Green Energy stays resource-first
    if ind == "green_energy":
        proj_type = (proj_type or "wind").lower()
        if proj_type == "wind":
            return {
                "resource_art": "Wind_Resource_Profile",
                "step_labels": ["1) Wind Resource", "2) Layout & Yield", "3) Engineering", "4) Schedule", "5) Cost/Economics"],
                "show_well_plan": False,
            }
        if proj_type == "solar":
            return {
                "resource_art": "Solar_Irradiance_Profile",
                "step_labels": ["1) Solar Resource", "2) Layout & Yield", "3) Engineering", "4) Schedule", "5) Cost/Economics"],
                "show_well_plan": False,
            }
        return {
            "resource_art": "Hydrogen_Demand_Profile",
            "step_labels": ["1) H2 Demand", "2) Layout & Yield", "3) Engineering", "4) Schedule", "5) Cost/Economics"],
            "show_well_plan": False,
        }

    # Default (Oil & Gas style)
    return {
        "resource_art": "Reservoir_Profiles",
        "step_labels": ["1) Reservoir Sim", "2) Well Plan", "3) Engineering", "4) Schedule", "5) Cost/Economics"],
        "show_well_plan": True,
    }

# ==== Pipeline step runners (safe optional imports) ====
def _resolve_entry(mod_candidates, func_candidates=("run", "main")):
    import importlib
    for m in mod_candidates:
        try:
            mod = importlib.import_module(m)
        except Exception:
            continue
        base = m.split(".")[-1]
        for fn_name in (*func_candidates, base):
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                return fn
    return None

# Try common module names; fall back to None (UI will show info)
subsurface_run = _resolve_entry([
    "modules.subsurface",
    "modules.reservoir_simulator",
    "decisionmate_core.reservoir_simulator",
    "decisionmate_core.subsurface",
])

engineering_run = _resolve_entry([
    "modules.engineering",
    "modules.process_flow_simulation",
    "decisionmate_core.process_flow_simulation",
])

schedule_run = _resolve_entry([
    "modules.schedule",
    "modules.schedule_developer",
    "decisionmate_core.schedule_developer",
])

cost_run = _resolve_entry([
    "modules.cost",
    "modules.cost_estimator",
    "modules.financial_analysis",
    "decisionmate_core.cost_estimator",
    "decisionmate_core.financial_analysis",
])

# IT pipeline runner (safe import + fallback)
try:
    from it_pipeline import run as run_it_pipeline
except Exception:
    try:
        from it_pipeline import run_it_pipeline  # if your file exports this name
    except Exception:
        def run_it_pipeline():
            import streamlit as st
            st.info("IT pipeline module not available.")

# --- Requirements view helper (fix for NameError) ---
try:
    from services.industry_gate_requirements import list_required_artifacts_industry_aware
except Exception:
    list_required_artifacts_industry_aware = lambda phase, ind: []

# in app.py (above render_pipeline)
from services.industry_gate_requirements import list_required_artifacts_industry_aware
try:
    from artifact_registry import get_latest, approve_artifact, save_artifact
except Exception:
    get_latest = approve_artifact = save_artifact = None





# ===== REPLACE WHOLE _open_ops_hub FUNCTION WITH THIS =====



# --- tolerant workspace opener ---


# Industries that should show PM Hub inside Workspace



def _safe_rerun():
    rr = getattr(st, "rerun", None)
    if callable(rr):
        rr()
    else:
        rr_old = getattr(st, "experimental_rerun", None)
        if callable(rr_old):
            rr_old()

def render_pipeline():
    import streamlit as st
    st.markdown("## Project Pipeline")

    # ---- context
    industry   = (st.session_state.get("project_industry")
                  or st.session_state.get("industry")
                  or "oil_gas").lower()
    phase_code = st.session_state.get("fel_stage", "FEL1")
    stage      = phase_code
    proj_type  = (st.session_state.get("green_project_type")
                  if industry == "green_energy" else None)

    # ---- common header: KPIs → requirements → timeline
    from services.registry import load_registry
    from services.kpis import render_kpis
    from services.history import render_timeline

    kpis = load_registry(industry, phase_code)
    render_kpis(kpis)

    st.markdown("---")
    render_requirements(industry, phase_code, proj_type)

    st.markdown("---")
    render_timeline(industry, phase_code)

    # ---- keep IDs aligned
    project_id = (
        st.session_state.get("active_project_id")
        or st.session_state.get("current_project_id")
        or "P-DEMO"
    )
    st.session_state["current_project_id"] = project_id

    phase_id = (
        st.session_state.get("current_phase_id")
        or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    )
    st.session_state["current_phase_id"] = phase_id

    # ========= Industry-specific hubs (early return) =========
    if industry == "it":
        # use the tolerant runner defined earlier (with fallbacks)
        run_it_pipeline()
        # right rail (use helpers already imported at top of app.py)
        with st.sidebar:
            st.markdown("### Pipeline Progress")
            pct, *_ = artifact_status_summary(phase_code)
            progress_bar(pct)
            right_rail_gate(phase_code, artifact_status_summary, st.session_state)
        return

    if industry == "healthcare":
        from workflows import pm_hub_healthcare as pmhc
        pmhc.render()
        return

    if industry == "manufacturing":
        from workflows import pm_hub_manufacturing as pmm
        pmm.render()
        return

    if industry == "aerospace_defense":
        from workflows import pm_hub_aerospace_defense as pma
        pma.render()
        return

    if industry == "government_infrastructure":
        from workflows import pm_hub_government_infrastructure as pmg
        pmg.render()
        return

    if industry in ("arch_construction", "architecture_construction"):
        from workflows import pm_hub_arch_construction as pmac
        pmac.render()
        return

    # ========= Green Energy (resource-first) =========
    if industry == "green_energy":
        st.info("Select your green energy project type.")
        st.session_state["green_project_type"] = st.selectbox(
            "Green project type",
            ["wind", "solar", "hydrogen"],
            index={"wind": 0, "solar": 1, "hydrogen": 2}.get(
                str(st.session_state.get("green_project_type", "wind")).lower(), 0
            ),
            key="green_project_type_select",
        )
        proj_type = str(st.session_state["green_project_type"]).lower()

        cfg = _ge_config(industry, proj_type)

        with st.sidebar:
            st.markdown("### Pipeline Progress")
            pct, *_ = artifact_status_summary(phase_code)
            progress_bar(pct)
            right_rail_gate(phase_code, artifact_status_summary, st.session_state)

        # registry helpers (safe)
        try:
            from artifact_registry import save_artifact, approve_artifact, get_latest
        except Exception:
            save_artifact = approve_artifact = get_latest = None

        subsurface_run  = globals().get("subsurface_run")
        engineering_run = globals().get("engineering_run")
        schedule_run    = globals().get("schedule_run")
        cost_run        = globals().get("cost_run")

        steps = cfg["step_labels"]
        t1, t2, t3, t4, t5 = st.tabs(steps)

        # Step 1 — resource inputs (per type)
        with t1:
            st.markdown(f"### 1) {steps[0]}")
            if proj_type == "wind":
                colA, colB, colC = st.columns(3)
                with colA:
                    mean_wind = st.number_input("Mean wind speed @ hub height (m/s)", value=7.5, min_value=0.0, step=0.1)
                with colB:
                    capacity_factor = st.number_input("Initial capacity factor (%)", value=38.0, min_value=0.0, max_value=100.0, step=0.5)
                with colC:
                    hub_height = st.number_input("Hub height (m)", value=100, min_value=1, step=1)
                roughness = st.selectbox(
                    "Terrain roughness class",
                    ["Offshore (0.0002)", "Open sea (0.003)", "Flat (0.01)", "Crop (0.05)", "Forest (0.3)"],
                    index=2,
                )
                uploaded = st.file_uploader("(Optional) Time series CSV (date,wind_mps)", type=["csv"])
                payload = {
                    "mean_wind_mps": mean_wind,
                    "capacity_factor_pct": capacity_factor,
                    "hub_height_m": hub_height,
                    "roughness": roughness,
                    "timeseries_csv_name": uploaded.name if uploaded else None,
                }
                res_art = cfg["resource_art"]
            elif proj_type == "solar":
                colA, colB, colC = st.columns(3)
                with colA:
                    ghi = st.number_input("GHI (kWh/m²/yr)", value=1900.0, min_value=0.0, step=10.0)
                with colB:
                    dc_ac_ratio = st.number_input("DC/AC ratio", value=1.2, min_value=0.8, max_value=1.6, step=0.05)
                with colC:
                    soiling_loss = st.number_input("Soiling loss (%)", value=3.0, min_value=0.0, max_value=20.0, step=0.5)
                tilt = st.number_input("Module tilt (°)", value=20, min_value=0, max_value=60, step=1)
                uploaded = st.file_uploader("(Optional) POA irradiance CSV (date,poa_kwh_m2)", type=["csv"])
                payload = {
                    "ghi_kwh_m2_yr": ghi,
                    "dc_ac_ratio": dc_ac_ratio,
                    "soiling_loss_pct": soiling_loss,
                    "tilt_deg": tilt,
                    "timeseries_csv_name": uploaded.name if uploaded else None,
                }
                res_art = cfg["resource_art"]
            else:  # hydrogen
                colA, colB, colC = st.columns(3)
                with colA:
                    demand_tpd = st.number_input("Hydrogen demand (t/day)", value=50.0, min_value=0.0, step=1.0)
                with colB:
                    availability = st.number_input("Availability (%)", value=95.0, min_value=0.0, max_value=100.0, step=0.5)
                with colC:
                    purity = st.number_input("Required purity (%)", value=99.9, min_value=0.0, max_value=100.0, step=0.1)
                payload = {"demand_tpd": demand_tpd, "availability_pct": availability, "purity_pct": purity}
                res_art = cfg["resource_art"]

            if save_artifact and approve_artifact:
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button(f"Save {res_art} (Draft)", key="ge_save_draft"):
                        save_artifact(project_id, phase_id, "Resource", res_art, payload, status="Draft")
                        st.success(f"{res_art} saved (Draft).")
                with c2:
                    if st.button(f"Save & Approve {res_art}", key="ge_save_approve"):
                        rec = save_artifact(project_id, phase_id, "Resource", res_art, payload, status="Pending")
                        approve_artifact(project_id, rec.get("artifact_id"))
                        st.success(f"{res_art} saved and Approved.")
                with c3:
                    st.caption("Approving will unlock downstream steps and chips.")

        # Step 2 — (no well plan in Green)
        with t2:
            st.info("Not applicable for this project type. Continue to the **Schedule** tab.")

        # Steps 3–5
        with t3:
            st.markdown("### 3) Engineering – Process Simulation & Equipment List")
            if callable(engineering_run): engineering_run(stage)
            else: st.info("Engineering module not available.")

        with t4:
            st.markdown("### 4) Schedule – WBS & Network")
            if callable(schedule_run): schedule_run(stage)
            else: st.info("Schedule module not available.")

        with t5:
            st.markdown("### 5) Cost & Economics")
            if callable(cost_run): cost_run(stage)
            else: st.info("Cost module not available.")
        return

    # ========= Fallback pipeline (O&G-style: Reservoir → Well Plan → Eng → Sched → Cost) =========
    cfg = _ge_config(industry, None)
    subsurface_run  = globals().get("subsurface_run")
    engineering_run = globals().get("engineering_run")
    schedule_run    = globals().get("schedule_run")
    cost_run        = globals().get("cost_run")

    steps = cfg["step_labels"]
    t1, t2, t3, t4, t5 = st.tabs(steps)

    # Step 1 — Reservoir Sim (if applicable)
    with t1:
        if cfg.get("show_well_plan", False):
            st.markdown("### 1) Reservoir Simulation")
            if callable(subsurface_run): subsurface_run(stage)
            else: st.info("Subsurface module not available.")
            st.divider()
            c1, c2 = st.columns([1, 1])
            with c1:
                st.caption("When Reservoir_Profiles is Approved, Engineering step can be seeded.")
            with c2:
                if st.button("Continue → Engineering", use_container_width=True, key="go_to_eng"):
                    _safe_rerun()
        else:
            st.info("Step 1 is not applicable for this industry. Continue to **Engineering**.")

    # Step 2 — Well Plan (O&G)
    with t2:
        if cfg.get("show_well_plan", False):
            st.markdown("### 2) Well Planning")
            try:
                from artifact_registry import get_latest, save_artifact
            except Exception:
                get_latest = save_artifact = None
            if not get_latest:
                st.info("Data registry not available.")
            else:
                latest = get_latest(project_id, "Reservoir_Profiles", phase_id)
                if not latest:
                    st.warning("Approve **Reservoir_Profiles** first.")
                else:
                    data = latest.get("data", {}) or {}
                    oil = float(data.get("avg_oil_rate", 3000))
                    target = st.number_input("Target plateau oil rate (bopd)", value=20000, min_value=1000)
                    per_well = st.number_input("Design per-well oil rate (bopd)", value=int(oil if oil > 0 else 3000), min_value=500)
                    wells = max(1, int(round(target / max(1, per_well))))
                    st.metric("Suggested wells", wells)
                    if st.button("Save Well Plan (Draft)", key="save_well_plan"):
                        save_artifact(project_id, phase_id, "Subsurface", "Well_Plan",
                                      {"target": target, "per_well": per_well, "wells": wells},
                                      status="Draft")
                        st.success("Well Plan saved (Draft).")
        else:
            st.info("Not applicable for this industry. Continue to the **Schedule** tab.")

    # Step 3 — Engineering
    with t3:
        st.markdown("### 3) Engineering – Process Simulation & Equipment List")
        if callable(engineering_run): engineering_run(stage)
        else: st.info("Engineering module not available.")
        st.divider()
        c1, c2 = st.columns([1, 1])
        with c1:
            st.caption("When Engineering concept is Approved, seed the schedule.")
        with c2:
            if st.button("Seed Schedule from Engineering", use_container_width=True, key="seed_sched_from_eng"):
                _seed_schedule_from_eng_now()
                st.success("Seeded schedule inputs from Engineering. Open the next tab.")

    # Step 4 — Schedule
    with t4:
        st.markdown("### 4) Schedule – WBS & Network")
        if callable(schedule_run): schedule_run(stage)
        else: st.info("Schedule module not available.")
        st.divider()
        c1, c2 = st.columns([1, 1])
        with c1:
            st.caption("When network is Approved, seed cost model.")
        with c2:
            if st.button("Seed Cost from Schedule", use_container_width=True, key="seed_cost_from_sched"):
                _seed_cost_from_schedule_now()
                st.success("Seeded cost model from schedule network.")

    # Step 5 — Cost
    with t5:
        st.markdown("### 5) Cost & Economics")
        if callable(cost_run): cost_run(stage)
        else: st.info("Cost module not available.")

    # ========= Fallback (no industry-specific pipeline) =========


# =============================================================================
# Page config & session init
# =============================================================================
# st.set_page_config(page_title="DecisionMate Rev4", layout="wide", page_icon="📊")

if "active_view" not in st.session_state:  st.session_state.active_view = None
if "module_info" not in st.session_state:  st.session_state.module_info = None
if "active_project_id" not in st.session_state: st.session_state.active_project_id = None
if "active_namespace" not in st.session_state: st.session_state.active_namespace = None
if "mode" not in st.session_state:         st.session_state.mode = "projects"  # "projects" | "ops"
if "ops_mode" not in st.session_state:     st.session_state.ops_mode = "daily_ops"
if "fel_stage" not in st.session_state:    st.session_state.fel_stage = "FEL1"
# ---- Governance defaults (must exist before launching modules)
if "team_members" not in st.session_state:
    st.session_state.team_members = {"Subsurface": [], "Engineering": [], "Cost": [], "Schedule": [], "Risk": []}
if "reviewers" not in st.session_state:
    st.session_state.reviewers = []
if "approvers" not in st.session_state:
    st.session_state.approvers = []
if "deliverables" not in st.session_state:
    st.session_state.deliverables = {"FEL1": [], "FEL2": [], "FEL3": [], "FEL4": []}
if "artifacts" not in st.session_state:
    st.session_state.artifacts = {}
if "rev3_scan_packages" not in st.session_state:
    st.session_state["rev3_scan_packages"] = []
# ---- Artifact service (global per session)
if "artifact_service" not in st.session_state:
    st.session_state.artifact_service = ArtifactService()
def _qm_lookup_by_module_path(module_path: str):
    """Return (title, func_name) from REV3_GROUPS for a given module_path."""
    for group_label, entries in REV3_GROUPS.items():
        for title, (mpath, fn) in entries.items():
            if mpath == module_path:
                return title, fn
    return None, None
# ---- Apply URL params once
qp = st.query_params
if "qp_applied" not in st.session_state:
    grp = qp.get("group")
    if grp in ("projects", "ops") and "mode" not in st.session_state:
        st.session_state.mode = grp
    sub = qp.get("ops_mode")
    if sub in ("daily_ops", "small_projects") and "ops_mode" not in st.session_state:
        st.session_state.ops_mode = sub
    st.session_state.qp_applied = True

# ===== AI Services router =====
if st.session_state.get("view") == "AI Services":
    try:
        from ai.hub import render as render_ai_hub
        render_ai_hub()
    except Exception as e:
        st.error(f"AI Services failed to load: {e}")
    st.stop()

# --- Quick Modules deep link support ---
if qp.get("view") == "quick":
    qm_mod = qp.get("qm_mod")
    qm_fn  = qp.get("qm_fn")
    if qm_mod:
        title, fn = _qm_lookup_by_module_path(qm_mod)
        if not fn:  # not found in catalog, fall back to query
            fn = qm_fn or "run"
            title = title or qm_mod.split(".")[-1].replace("_"," ").title()
        st.session_state["view"] = "Quick Modules"
        st.session_state["qm_active"] = {
            "title": title,
            "module_path": qm_mod,
            "func_name": fn,
        }


# =============================================================================
# Title / module runner
# =============================================================================
st.title("DecisionMate Rev4")
st.caption("Industry-linked hubs with FEL and Ops views.")

st.markdown("---")

# === Pipeline view router (must be BEFORE 'Modules' and PM Hub blocks) ===
if st.session_state.get("view") in ("Workspace", "Working Area", "Pipeline"):  # legacy alias supported
    if _locked_group() == "ops":
        st.warning("Workspace (PM) is disabled while an **Ops** project is active. Click **Reset (unlock)** in the sidebar to switch.")
        st.stop()
    render_pipeline()
    st.stop()


# ============================================
# Native Rev4 Modules (REGISTRY-based)
# ============================================
if st.session_state["view"] == "Modules":
    st.subheader("Modules")

    if MODULES_IMPORT_ERROR:
        st.info("Using built-in fallback since no external modules are loaded.")
        st.caption(MODULES_IMPORT_ERROR)

    module_names = sorted(list(REGISTRY.keys()))
    if not module_names:
        st.warning("No modules registered.")
        st.stop()

    # honor deep-link from other pages
    requested = st.session_state.pop("force_open_module", None)
    if requested:
        st.session_state["open_module"] = requested

    open_mod = st.session_state.get("open_module")
    default_idx = module_names.index(open_mod) if open_mod in module_names else 0

    mod = st.selectbox("Open Module", module_names, index=default_idx, key="modules_selectbox")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Launch Module", key="btn_launch_module"):
            st.session_state["open_module"] = mod
            st.session_state["current_project_id"] = st.session_state.get("active_project_id") or "P-DEMO"
            st.session_state["current_phase_id"]   = f"PH-{st.session_state.get('fel_stage','FEL1')}"
            st.rerun()
    with c2:
        if st.button("Close Module", key="btn_close_module"):
            st.session_state.pop("open_module", None)
            st.rerun()

    active = st.session_state.get("open_module")
    if active and active in REGISTRY:
        stage = st.session_state.get("fel_stage", "FEL1")
        st.session_state["fel_stage"] = stage  # <-- ensure stage is set
        st.session_state["view"] = "Modules"   # <-- ensure view is preserved
        st.markdown(f"### {active}")
        fn = REGISTRY[active]
        try:
            fn(stage)
        except Exception as ex:
            st.error(f"{active} crashed: {ex}")
    else:
        st.info("Select a module and click Launch Module.")

    # prevent hubs from rendering under Modules
    st.stop()



# ============================================
# Quick Modules (Rev-3 exact catalog)
# ============================================
if st.session_state["view"] == "Quick Modules":
    st.title("⚡ Quick Modules (Rev-3 Tools)")
    st.caption("Exactly the Rev-3 groups, launched with the Rev-3 calling convention (T dict).")

    # --- Active tool HOST (top of page so it's visible immediately) ---
    active = st.session_state.get("qm_active")
    if active:
        top_left, top_right = st.columns([1, 9])
        with top_left:
            if st.button("Close", key="qm_close_top"):
                st.session_state.pop("qm_active", None)
                try:
                    new_qp = dict(st.query_params)
                    new_qp.pop("qm_mod", None)
                    new_qp.pop("qm_fn", None)
                    if new_qp.get("view") == "quick":
                        new_qp.pop("view", None)
                    st.query_params.from_dict(new_qp)
                except Exception:
                    pass
                st.rerun()

        with top_right:
            st.subheader(f"▶ {active['title']}")
        try:
            run_legacy(active["module_path"], active["func_name"])
        except Exception as e:
            st.error(f"Could not run {active['title']}: {e}")
            st.exception(e)
        st.markdown("---")

    # --- Search box for the catalog ---
    query = st.text_input("Search", key="qm_search").strip().lower()

    # --- Catalog list (Run only sets state; UI renders in the host above) ---
    for group_label, entries in REV3_GROUPS.items():
        filtered = (
            {k: v for k, v in entries.items()
             if query in k.lower() or query in ".".join(v).lower()}
            if query else entries
        )
        if not filtered:
            continue

        with st.expander(group_label, expanded=True):
            for idx, (ui_name, (module_path, func_name)) in enumerate(filtered.items()):
                c1, c2 = st.columns([6, 1])
                with c1:
                    st.write(f"**{ui_name}**")
                    st.caption(f"`{module_path}.{func_name}`")
                with c2:
                    base = module_path.split(".")[-1]
                    exists = (
                        importlib.util.find_spec(module_path) is not None
                        or importlib.util.find_spec(f"modules.{base}") is not None
                        or importlib.util.find_spec(base) is not None
                        or importlib.util.find_spec(f"decisionmate_core.{base}") is not None
                    )
                    btn_key = f"qm_run__{group_label}__{ui_name}__{idx}"  # unique
                    if st.button("Run", key=btn_key, disabled=not exists):
                        st.session_state["qm_active"] = {
                            "title": ui_name,
                            "module_path": module_path,
                            "func_name": func_name,
                        }
                        # write deep-link so this state is shareable
                        try:
                            st.query_params.from_dict({"view": "quick", "qm_mod": module_path, "qm_fn": func_name})
                        except Exception:
                            pass
                        st.rerun()

    st.stop()

# =============================================================================
# Sidebar — context, projects, legacy modules, data I/O
# =============================================================================
# --- PREFETCH project industry so we can lock the dropdown this run -------------
_pref_proj_industry = st.session_state.get("project_industry")
try:
    if st.session_state.get("active_project_id") and st.session_state.get("active_namespace"):
        _meta = load_project_doc(
            st.session_state.get("username", "Guest"),
            st.session_state["active_namespace"],
            st.session_state["active_project_id"],
            "meta",
        ) or {}
        if isinstance(_meta, dict) and _meta.get("industry"):
            _pref_proj_industry = _meta["industry"]
            st.session_state["project_industry"] = _pref_proj_industry
except Exception:
    pass
# ------------------------------------------------------------------------------
# --- discover industries from workflows so lists never go stale ---
import pkgutil

def _discover_industries_from_workflows() -> set[str]:
    found = set()
    try:
        import workflows
        for m in pkgutil.iter_modules(workflows.__path__):
            name = m.name
            if name.startswith("pm_hub_"):
                found.add(name[len("pm_hub_"):])
            if name.startswith("ops_hub_"):
                found.add(name[len("ops_hub_"):])
    except Exception:
        pass
    return found

def _industry_choices() -> list[str]:
    base = list(getattr(TAXONOMY, "industries", [
        "oil_gas","green_energy","it","healthcare",
        "government_infrastructure","aerospace_defense",
        "manufacturing","arch_construction",
    ]))
    discovered = _discover_industries_from_workflows()
    return sorted(set(base) | discovered)


with st.sidebar:
    st.markdown("## Context")
    st.button(
        "✖ Close navigation" if st.session_state.get("nav_open") else "☰ Open navigation",
        key="btn_nav_sidebar_toggle_app",
        use_container_width=True,
        on_click=_toggle_nav,
    )

    # If a project is active and we know its industry, lock the dropdown
    industry_locked = bool(st.session_state.get("active_project_id")) and bool(st.session_state.get("project_industry"))
    if industry_locked:
        st.session_state["industry"] = st.session_state["project_industry"]

    industry = st.selectbox(
        "Industry",
        _industry_choices(),
        index=0,
        key="industry",
        disabled=industry_locked
    )
    if industry_locked:
        st.caption(f"Project industry: {st.session_state['project_industry']}")

    username = st.text_input("Username", value="Guest", key="username")

    # --- NEW: Mode is inferred from the current view (no radios here)
    st.session_state.mode = _mode_from_view(st.session_state.get("view", "PM Hub"))
# If locked by an active project, force the mode so the other group's UI is disabled
    __lk = _locked_group()
    if __lk:
        st.session_state.mode = __lk

    # Keep a default sub-mode in state; the actual selector will live inside Ops Hub
    st.session_state.setdefault("ops_mode", "daily_ops")

    # Namespace depends on inferred mode
    if st.session_state.mode == "ops":
        requested_namespace = f"{industry}:ops:{st.session_state.ops_mode}"
    else:
        requested_namespace = f"{industry}:projects"

    # If a project is active, stick to its namespace (prevents list/UI from flipping)
    namespace = st.session_state.active_namespace or requested_namespace


    st.markdown("## Projects")
    if st.session_state.mode == "projects":
        # PM project creation
        new_pm_name = st.text_input("New PM project name", value="", key="inp_new_pm")
        if st.button("Create PM Project", key="btn_create_pm_project") and new_pm_name.strip():
            ns = f"{industry}:projects"
            pid = create_project(username, ns, new_pm_name.strip())

            # NEW ✅: save project meta with chosen industry
            try:
                save_project_doc(username, ns, pid, "meta", {"industry": industry, "created_by": username})
            except Exception:
                pass

            st.success(f"Created PM project: {pid}")
            st.session_state.active_project_id = pid
            st.session_state.active_namespace = ns
            try: st.query_params.from_dict({"group": "projects"})
            except Exception: pass
            st.rerun()

    else:
        pretty = "Daily Ops" if st.session_state.ops_mode == "daily_ops" else "Small Projects"
        new_ops_name = st.text_input(f"New {pretty} project name", value="", key="inp_new_ops")
        if st.button("Create Ops Project", key="btn_create_ops_project") and new_ops_name.strip():
            ns = f"{industry}:ops:{st.session_state.ops_mode}"
            pid = create_project(username, ns, new_ops_name.strip())

            # NEW ✅: save project meta with chosen industry
            try:
                save_project_doc(username, ns, pid, "meta", {"industry": industry, "created_by": username})
            except Exception:
                pass

            st.success(f"Created {pretty} project: {pid}")
            st.session_state.active_project_id = pid
            st.session_state.active_namespace = ns
            try: st.query_params.from_dict({"group": "ops", "ops_mode": st.session_state.ops_mode})
            except Exception: pass
            st.rerun()


    projects = list_projects(username, namespace)
    proj_ids = list(projects.keys())
    NONE = "— none —"

    if proj_ids:
        options = [NONE] + proj_ids
        if (st.session_state.get("active_namespace") == namespace and st.session_state.get("active_project_id") in proj_ids):
            sel_index = options.index(st.session_state.active_project_id)
        else:
            sel_index = 0
            st.session_state.active_project_id = None
            st.session_state.active_namespace = None

        selected = st.selectbox(
            "Select project",
            options,
            index=sel_index,
            format_func=lambda x: (x if x == NONE else projects.get(x, {}).get("name", x)),
            key="select_project_id",
        )
        if selected == NONE:
            st.session_state.active_project_id = None
            st.session_state.active_namespace = None
        else:
            st.session_state.active_project_id = selected
            st.session_state.active_namespace = namespace
    else:
        st.info("No projects yet. Create one above.")
        st.session_state.active_project_id = None
        st.session_state.active_namespace = None
    # NEW ✅: resolve and remember project_industry from saved meta
    project_industry = industry  # default to sidebar choice
    try:
        if st.session_state.active_project_id and st.session_state.active_namespace:
            meta = load_project_doc(
                username,
                st.session_state.active_namespace,
                st.session_state.active_project_id,
                "meta"
            ) or {}
            if isinstance(meta, dict) and meta.get("industry"):
                project_industry = meta["industry"]
    except Exception:
        pass
    st.session_state["project_industry"] = project_industry
    # (optional) visible hint:
    st.caption(f"Project industry: {project_industry}")

    mode_locked = (st.session_state.active_project_id is not None and st.session_state.active_namespace == namespace)
    if mode_locked: st.caption("Group locked to this project. Choose “— none —” to switch.")
    if st.button("Reset (unlock)", key="btn_reset_unlock"):
        st.session_state.active_project_id = None
        st.session_state.active_namespace = None
        st.session_state.qp_applied = False
        try: st.query_params.from_dict({})
        except Exception: pass
        st.rerun()

    st.markdown("## Artifact Status")
    svc = st.session_state.artifact_service
    try:
        for art_type, discipline in PRODUCER.items():
            rec = svc.latest(art_type)
            if rec:
                status = "✅ Approved" if rec.approved else "⏳ Pending"
                if rec.stale: status = "⚠️ Stale"
                st.write(f"**{art_type}** ({discipline}): {status} v{rec.version}")
    except Exception:
        st.caption("Artifact status unavailable.")



    st.markdown("## Data")
    ns_industry = (namespace.split(":")[0]) if namespace else industry
    if st.session_state.mode == "projects":
        data_label = "PM document key"; default_doc = f"{ns_industry}_projects"; load_label = "Load PM Data"
        help_text = "Snapshot of PM hub (KPIs, FEL, gates, etc.)"
    else:
        pretty = st.session_state.ops_mode
        data_label = f"Ops ({pretty}) document key"; default_doc = f"{ns_industry}_ops_{st.session_state.ops_mode}"
        load_label = f"Load Ops Data ({pretty})"; help_text = "Snapshot of Ops hub for the selected sub-mode"

    doc_key = st.text_input(data_label, value=default_doc, key=f"doc_key_{namespace}", help=help_text)

    if st.button(load_label, key=f"btn_load_{namespace}"):
        if st.session_state.active_project_id:
            payload = load_project_doc(username, namespace, st.session_state.active_project_id, doc_key)
            st.success("Loaded (if found). See JSON below.")
            if payload: st.json(payload)
        else:
            st.warning("Select a project first.")

# =============================================================================
# Context ids for Hub views
# =============================================================================
PROJECT_ID = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
PHASE_ID   = st.session_state.get("current_phase_id", "PH-FEL1")
PHASE_CODE = "FEL1"  # hook to your phase selector when ready

# Process any backlog events on load (logging only in manual mode)
process_events(PROJECT_ID)
# =========================
# OPS HUB VIEW (separate)
# =========================
if st.session_state["view"] == "Ops Hub":
    if _locked_group() == "projects":
        st.warning("Ops Hub is disabled while a **PM** project is active. Click **Reset (unlock)** in the sidebar to switch.")
        st.stop()

    # Add industry selector for Ops Hub
    ops_industry = st.session_state.get("project_industry") or st.session_state.get("industry", "oil_gas")


    pretty = {
        "oil_gas": "Oil & Gas",
        "green_energy": "Green Energy",
        "it": "IT",
        "healthcare": "Healthcare",
        "government_infrastructure": "Government & Infrastructure",
        "aerospace_defense": "Aerospace & Defense",
        "manufacturing": "Manufacturing",
        
    }.get(ops_industry, ops_industry.title())

    st.subheader(f"🛠 Ops Hub — {pretty}")

    submode = st.radio(
        "Sub-mode",
        ["daily_ops", "small_projects", "call_center"],
        horizontal=True,
        key="ops_mode",
    )
# Render the selected Ops sub-mode using the tolerant router
    if not open_ops_hub(ops_industry, st.session_state.get("ops_mode", "daily_ops")):
        # Fallback: show the generic requirements page if the hub didn't render
        render_requirements(ops_industry, PHASE_CODE)

    st.stop()  # Prevent the rest of the page from drawing twice

# app.py
import importlib, inspect
import streamlit as st

def open_ops_hub(industry: str, submode: str) -> bool:
    """Open the Ops Hub for an industry and route special submodes (e.g., call_center)."""
    try:
        from services.industries import route as industries_route
        module_path, entry = industries_route(industry, "ops")
    except Exception as e:
        st.error(f"Ops route error for {industry}: {e}")
        return False

    # --- Try the industry hub first
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        st.error(f"Cannot import Ops module '{module_path}': {e}")
        return False

    candidates = [
        getattr(mod, entry, None) if entry else None,
        getattr(mod, "render", None),
        getattr(mod, "run", None),
    ]
    if not any(callable(c) for c in candidates):
        # try submode-named entries in the hub
        sm = (submode or "daily_ops").strip()
        candidates.extend([
            getattr(mod, sm, None),
            getattr(mod, f"render_{sm}", None),
            getattr(mod, f"{sm}_view", None),
        ])
    fn = next((c for c in candidates if callable(c)), None)

    # --- If hub doesn't implement 'call_center', route to the external tool
    if not fn and (submode or "").strip() == "call_center":
        try:
            from ops_call_center import render as call_center_render
            call_center_render(industry=industry, submode=submode)
            st.caption("✅ Opened Call Center tool.")
            return True
        except Exception as e:
            st.error(f"Call Center failed: {e}")
            return False

    if not fn:
        st.error(
            f"Ops Hub module '{module_path}' has no callable entry. "
            f"Tried: {entry!r} → render → run → {submode} → render_{submode} → {submode}_view"
        )
        return False

    # --- Call the hub entry with best-effort kwargs
    try:
        params = set(inspect.signature(fn).parameters.keys())
    except Exception:
        params = set()
    if params:
        kwargs = {}
        if "industry" in params: kwargs["industry"] = industry
        if "submode"  in params: kwargs["submode"]  = submode
        if "mode"     in params: kwargs["mode"]     = submode
        if "st"       in params: kwargs["st"]       = st
        try:
            fn(**kwargs)
            return True
        except TypeError:
            pass

    for args in [(), (submode,), (industry,), (industry, submode)]:
        try:
            fn(*args)
            return True
        except TypeError:
            continue

    try:
        fn()
        return True
    except Exception as e:
        st.error(f"Ops callable failed: {e}")
        return False




# =============================================================================
# PM HUB VIEW ONLY
# =============================================================================
active_industry = st.session_state.get("project_industry", industry)
if st.session_state["view"] == "PM Hub":
    if _locked_group() == "ops":
        st.warning("PM Hub is disabled while an **Ops** project is active. Click **Reset (unlock)** in the sidebar to switch.")
        st.stop()


    st.subheader("📊 PM Hub — Live KPIs")
        # Jump to Pipeline (guided FEL flow)
    c_l, c_r = st.columns([1, 5])
    with c_l:
        if st.button("▶ Open Workspace", key="pmhub_open_workspace"):
            st.session_state["view"] = "Workspace"
            st.rerun()
    with c_r:
# Show an industry-aware caption (no O&G bias)
        _active_ind = st.session_state.get("project_industry", st.session_state.get("industry", "oil_gas"))
        _ge = _ge_config(_active_ind, st.session_state.get("green_project_type"))
        _labels = [s.split(") ", 1)[1] if ") " in s else s for s in _ge["step_labels"]]
        _labels = [x for x in _labels if x.lower() != "not applicable"]
        st.caption("Pipeline = guided path: " + " → ".join(_labels) + ". Uses the same artifacts shown here.")


    col1, col2, col3 = st.columns(3)
    with col1:
        wbs = get_latest(PROJECT_ID, "WBS", PHASE_ID)
        st.metric("WBS nodes", len(wbs.get("data", {}).get("nodes", [])) if wbs else 0)
    with col2:
        sched = get_latest(PROJECT_ID, "Schedule_Network", PHASE_ID)
        st.metric("Critical Path (days)", len(sched.get("data", {}).get("critical_path_ids", [])) if sched else 0)
    with col3:
        cost = get_latest(PROJECT_ID, "Cost_Model", PHASE_ID)
        st.metric("CAPEX items", len(cost.get("data", {}).get("capex_breakdown", [])) if cost else 0)

    st.divider()
    st.markdown("### Required Artifacts for Phase")
    req = required_artifacts_for_phase(PHASE_CODE)

    for r in req:
        latest = get_latest(PROJECT_ID, r["type"], PHASE_ID)
        status = latest.get("status") if latest else "Missing"
        st.write(f"**{r['workstream']} – {r['type']}**: {status}")

    st.divider()
    st.markdown("### Recent Events")
    for e in read_events(PROJECT_ID)[:10]:
        st.caption(f"{e['ts']} — {e['event_type']} — {e['payload']}")

    # --- Visuals: Mini Gantt & Risk Heatmap ---
    st.divider()
    st.markdown("### Visuals")
    col_gantt, col_risk = st.columns([2, 1])

    # ============== Mini Gantt from Schedule_Network ==============
    with col_gantt:
        st.markdown("#### Mini Gantt (from Schedule_Network)")
        try:
            sched_rec = get_latest(PROJECT_ID, "Schedule_Network", PHASE_ID)
            if sched_rec and isinstance(sched_rec.get("data"), dict):
                data = sched_rec["data"]
                acts = data.get("activities", [])
                if acts:
                    import datetime as _dt
                    try:
                        import pandas as _pd
                        import altair as _alt
                    except Exception:
                        _pd = None; _alt = None

                    base_str = (data.get("start_date") or _dt.date.today().isoformat())
                    try: base_date = _dt.datetime.fromisoformat(base_str).date()
                    except Exception: base_date = _dt.date.today()

                    dur = {a["id"]: int(a.get("dur_days", 1)) for a in acts}
                    preds = {a["id"]: list(a.get("predecessors", [])) for a in acts}
                    name  = {a["id"]: a.get("name", a["id"]) for a in acts}
                    starts, finishes = {}, {}
                    remaining = set(dur.keys())
                    for _ in range(0, len(remaining) + 5):
                        progressed = False
                        for aid in list(remaining):
                            ps = preds.get(aid, [])
                            if all(p in finishes for p in ps):
                                es = 0 if not ps else max(finishes[p] for p in ps)
                                starts[aid] = es
                                finishes[aid] = es + max(1, dur[aid])
                                remaining.remove(aid)
                                progressed = True
                        if not progressed: break

                    rows = []
                    for aid in finishes:
                        s_off = starts[aid]; f_off = finishes[aid]
                        s_date = base_date + _dt.timedelta(days=s_off)
                        f_date = base_date + _dt.timedelta(days=f_off)
                        rows.append({"Task": name.get(aid, aid), "Start": s_date, "Finish": f_date, "Days": max(1, dur.get(aid, 1))})

                    if rows and _pd is not None and _alt is not None:
                        df = _pd.DataFrame(rows)
                        chart = _alt.Chart(df).mark_bar().encode(
                            x=_alt.X('Start:T', title=''), x2='Finish:T',
                            y=_alt.Y('Task:N', sort='-x', title=''),
                            tooltip=['Task', 'Start:T', 'Finish:T', 'Days:Q']
                        ).properties(height=300)
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.caption("Altair/pandas not available — showing table.")
                        st.write(rows or "No activities found.")
                else:
                    st.caption("No activities in Schedule_Network yet.")
            else:
                st.caption("No Schedule_Network artifact yet.")
        except Exception as ex:
            st.warning(f"Gantt render issue: {ex}")

    # ============== Risk Heatmap from Risk_Register ==============
    with col_risk:
        st.markdown("#### Risk Heatmap (Likelihood × Impact)")
        try:
            risk_rec = get_latest(PROJECT_ID, "Risk_Register", PHASE_ID)
            raw = ""
            if risk_rec and isinstance(risk_rec.get("data"), dict):
                raw = str(risk_rec["data"].get("risk_table_raw", ""))

            if raw.strip():
                try:
                    import pandas as _pd
                    import altair as _alt
                except Exception:
                    _pd = None; _alt = None

                lik, imp = [], []
                for line in raw.splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        try:
                            L = int(parts[-2]); I = int(parts[-1])
                        except Exception:
                            try:
                                L = int(parts[2]); I = int(parts[3])
                            except Exception:
                                continue
                        lik.append(L); imp.append(I)

                if lik and imp:
                    if _pd is not None and _alt is not None:
                        df = _pd.DataFrame({"Likelihood": lik, "Impact": imp})
                        df["Likelihood"] = df["Likelihood"].clip(1, 5)
                        df["Impact"] = df["Impact"].clip(1, 5)
                        agg = df.groupby(["Likelihood", "Impact"]).size().reset_index(name="Count")
                        heat = _alt.Chart(agg).mark_rect().encode(
                            x=_alt.X('Impact:O', title='Impact'),
                            y=_alt.Y('Likelihood:O', title='Likelihood'),
                            color=_alt.Color('Count:Q', title='Count'),
                            tooltip=['Likelihood:O', 'Impact:O', 'Count:Q']
                        ).properties(height=300)
                        st.altair_chart(heat, use_container_width=True)
                    else:
                        st.caption("Altair/pandas not available — showing counts.")
                        st.write(list(zip(lik, imp)))
                else:
                    st.caption("Risk table found but couldn’t parse numbers yet.")
            else:
                st.caption("No Risk_Register artifact yet.")
        except Exception as ex:
            st.warning(f"Risk heatmap issue: {ex}")
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()
    st.markdown("---")

    # ============== Cost & CAPEX Visuals ==============
    st.divider()
    st.markdown("### Cost & CAPEX")
    col_cf, col_capex = st.columns([2, 1])

    # Cash-flow sparkline
    with col_cf:
        st.markdown("#### Cash-flow Sparkline")
        try:
            cost_rec = get_latest(PROJECT_ID, "Cost_Model", PHASE_ID)
            if cost_rec and isinstance(cost_rec.get("data"), dict):
                data = cost_rec["data"]; cash = data.get("cashflow", [])
                if cash:
                    try: import pandas as _pd
                    except Exception: _pd = None
                    rows = []
                    for r in cash:
                        d = r.get("date")
                        net = float(r.get("inflow", 0)) - float(r.get("outflow", 0))
                        if d: rows.append((d, net))
                    if rows:
                        rows.sort(key=lambda x: x[0])
                        if _pd is not None:
                            df = _pd.DataFrame(rows, columns=["date", "net"])
                            df["cum"] = df["net"].cumsum()
                            st.line_chart(df.set_index("date")["cum"], height=180)
                            st.caption("Cumulative net cash (inflow − outflow)")
                        else:
                            st.write(rows)
                    else:
                        st.caption("Cashflow present but has no dated entries.")
                else:
                    tot_capex = data.get("total_capex"); tot_opex = data.get("total_opex")
                    if tot_capex is not None or tot_opex is not None:
                        c1_, c2_ = st.columns(2)
                        if tot_capex is not None: c1_.metric("Total CAPEX", f"{tot_capex:,.0f}")
                        if tot_opex is not None: c2_.metric("Annual OPEX", f"{tot_opex:,.0f}")
                    else:
                        st.caption("No cashflow yet. Freeze a Cost Model or generate from Schedule.")
            else:
                st.caption("No Cost_Model artifact yet.")
        except Exception as ex:
            st.warning(f"Cash-flow render issue: {ex}")

    # CAPEX by WBS
    with col_capex:
        st.markdown("#### CAPEX by WBS")
        try:
            cost_rec = get_latest(PROJECT_ID, "Cost_Model", PHASE_ID)
            if cost_rec and isinstance(cost_rec.get("data"), dict):
                data = cost_rec["data"]; capex_brk = data.get("capex_breakdown", [])
                if capex_brk:
                    try:
                        import pandas as _pd; import altair as _alt
                    except Exception:
                        _pd = None; _alt = None
                    rows = [{"WBS": str(it.get("wbs_id","—")), "Cost": float(it.get("cost",0))} for it in capex_brk]
                    if rows and _pd is not None and _alt is not None:
                        df = _pd.DataFrame(rows)
                        chart = _alt.Chart(df).mark_bar().encode(
                            x=_alt.X("Cost:Q", title=""),
                            y=_alt.Y("WBS:N", sort='-x', title=""),
                            tooltip=["WBS","Cost"]
                        ).properties(height=180)
                        st.altair_chart(chart, use_container_width=True)
                        st.metric("Total CAPEX", f"{df['Cost'].sum():,.0f}")
                    else:
                        st.write(rows or "No CAPEX items found.")
                else:
                    st.caption("No CAPEX breakdown yet.")
            else:
                st.caption("No Cost_Model artifact yet.")
        except Exception as ex:
            st.warning(f"CAPEX render issue: {ex}")

    # ============== WBS & Economics ==============
    st.divider()
    st.markdown("### Structure & Economics")
    col_wbs, col_econ = st.columns([1, 1])

    # WBS donut
    with col_wbs:
        st.markdown("#### WBS Nodes by Level")
        try:
            wbs_rec = get_latest(PROJECT_ID, "WBS", PHASE_ID)
            level_counts = {}
            if wbs_rec and isinstance(wbs_rec.get("data"), dict):
                wbs_data = wbs_rec["data"]
                nodes = wbs_data.get("nodes", [])
                if nodes:
                    for n in nodes:
                        nid = str(n.get("id", "1"))
                        lvl = nid.count(".") + 1
                        level_counts[lvl] = level_counts.get(lvl, 0) + 1
                else:
                    raw = str(wbs_data.get("wbs_raw", "")).splitlines()
                    for line in raw:
                        token = line.strip().split()[0] if line.strip() else ""
                        if token:
                            lvl = token.count(".") + 1
                            level_counts[lvl] = level_counts.get(lvl, 0) + 1
            if level_counts:
                try:
                    import pandas as _pd; import altair as _alt
                    df = _pd.DataFrame([{"Level": int(k), "Count": int(v)} for k, v in sorted(level_counts.items())])
                    donut = _alt.Chart(df).mark_arc(innerRadius=60).encode(
                        theta=_alt.Theta("Count:Q"),
                        color=_alt.Color("Level:N"),
                        tooltip=["Level:N","Count:Q"]
                    ).properties(height=260)
                    st.altair_chart(donut, use_container_width=True)
                except Exception:
                    st.write(level_counts)
            else:
                st.caption("No WBS data yet. Approve a WBS or paste WBS text in the Schedule module.")
        except Exception as ex:
            st.warning(f"WBS donut issue: {ex}")

    # Econ summary
    with col_econ:
        st.markdown("#### Economics (NPV / IRR)")
        try:
            cm = get_latest(PROJECT_ID, "Cost_Model", PHASE_ID)
            npv_val = None; irr_val = None
            if cm and isinstance(cm.get("data"), dict):
                d = cm["data"]
                if isinstance(d.get("npv"), (int, float)): npv_val = float(d["npv"])
                if isinstance(d.get("irr"), (int, float)): irr_val = float(d["irr"])
                cash = d.get("cashflow", []); wacc = float(d.get("wacc", 0.1))
                if cash:
                    import datetime as _dt
                    flows = []
                    for r in cash:
                        try: dt = _dt.datetime.fromisoformat(str(r.get("date"))).date()
                        except Exception: continue
                        net = float(r.get("inflow",0)) - float(r.get("outflow",0))
                        flows.append((dt, net))
                    flows.sort(key=lambda x: x[0])
                    if flows:
                        base = flows[0][0]
                        def _years(d0, d1): return (d1 - d0).days / 365.0
                        xnpv = sum(v / ((1.0 + wacc) ** _years(base, dt)) for dt, v in flows)
                        if npv_val is None: npv_val = xnpv
                        if irr_val is None:
                            def f(rate):  return sum(v / ((1.0 + rate) ** _years(base, dt)) for dt, v in flows)
                            def df(rate): return sum(-_years(base, dt) * v / ((1.0 + rate) ** (_years(base, dt)+1e-12)) for dt, v in flows)
                            rate = 0.1
                            for _ in range(50):
                                try:
                                    fr = f(rate); dfr = df(rate)
                                    if abs(dfr) < 1e-12: break
                                    step = fr / dfr; rate -= step
                                    if abs(step) < 1e-6: break
                                except Exception: break
                            if -0.9999 < rate < 10: irr_val = rate
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("NPV (XNPV if computed)", f"{npv_val:,.0f}" if npv_val is not None else "—")
            with c2: st.metric("IRR (XIRR if computed)", f"{irr_val*100:,.2f}%" if irr_val is not None else "—")
            with c3:
                if cm and isinstance(cm.get("data"), dict):
                    d = cm["data"]; st.metric("WACC", f"{float(d.get('wacc', 0.1))*100:,.2f}%")
                else:
                    st.metric("WACC", "—")
            if not cm:
                st.caption("No Cost_Model yet. Freeze a Cost Model or generate from Schedule.")
        except Exception as ex:
            st.warning(f"Econ summary issue: {ex}")

    # Quick Demo Actions
    st.markdown("### Quick Demo Actions")
    colA, colB, colC = st.columns(3)
    with colA:
        if st.button("Seed Resource Profile (Draft)"):
            if active_industry == "green_energy":
                # Seed a generic green resource (edit as you like)
                save_artifact(PROJECT_ID, PHASE_ID, "Resource", "Wind_Resource_Profile", {
                    "mean_wind_m_s": 7.5, "weibull_k": 2.1, "weibull_c": 8.0,
                    "ti_pct": 12.0
                })
            else:
                save_artifact(PROJECT_ID, PHASE_ID, "Subsurface", "Reservoir_Profiles", {
                    "dates": ["2026-01-01", "2026-02-01"],
                    "oil_rate": [1500, 1480], "gas_rate": [2.3, 2.2], "water_rate": [0.1, 0.12],
                    "cum_oil": 1.2e6, "cum_gas": 2.5e6, "cum_water": 0.05e6,
                })

    with colB:
        if st.button("Approve Latest Resource Profile"):
            if active_industry == "green_energy":
                latest = get_latest(PROJECT_ID, "Wind_Resource_Profile", PHASE_ID) or \
                        get_latest(PROJECT_ID, "Solar_Irradiance_Profile", PHASE_ID) or \
                        get_latest(PROJECT_ID, "Hydrogen_Demand_Profile", PHASE_ID)
            else:
                latest = get_latest(PROJECT_ID, "Reservoir_Profiles", PHASE_ID)
            if latest:
                approve_artifact(PROJECT_ID, latest["artifact_id"])
                drain_events(PROJECT_ID)

    with colC:
        if st.button("Seed Risk Register"):
            save_artifact(PROJECT_ID, PHASE_ID, "Risk", "Risk_Register", {
                "risks": [{"id": "R1", "title": "Resource uncertainty", "likelihood": 3, "impact": 4, "score": 12}]
            }, status=_initial_status())


    st.markdown("---")


    # Action Center — human-in-the-loop approvals
    st.markdown("### Action Center (Pending Artifacts)")
    _pending_types = ["PFD_Package","Equipment_List","Utilities_Load","WBS","Schedule_Network","Long_Lead_List","Cost_Model","Risk_Register","QA_Scorecard","Coaching_Plan","Shift_Handover","KPI_Snapshot"]
    cols = st.columns(3); idx = 0
    for _t in _pending_types:
        rec = get_latest(PROJECT_ID, _t, PHASE_ID)
        if rec and rec.get("status") == "Pending":
            with cols[idx % 3]:
                st.write(f"**{_t}** — Pending")
                if st.button(f"Approve {_t}", key=f"approve__{_t}"):
                    approve_artifact(PROJECT_ID, rec["artifact_id"])
                    drain_events(PROJECT_ID)
            idx += 1
    if idx == 0:
        st.caption("No pending artifacts right now.")

    # Phase Swimlane & Gate
    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        st.markdown("### Phase Swimlane & Gate")
        render_swimlane(PROJECT_ID, PHASE_CODE, PHASE_ID)
    with col_g2:
        st.markdown("### Gate Check")
        result = check_gate_ready(PROJECT_ID, PHASE_CODE, PHASE_ID)
        if result["ready"]:
            st.success("All required artifacts are Approved. You can pass the gate.")
            if st.button("✅ Pass Gate (mark Exit Criteria met)"):
                st.session_state["gate_status"] = "Approved"
                st.toast("Gate approved.")
        else:
            if result["missing"]:
                st.error("Missing artifacts:\n- " + "\n- ".join(result["missing"]))
            if result["drafts"]:
                st.warning("Not approved yet:\n- " + "\n- ".join(result["drafts"]))
            st.button("🔒 Gate Locked", disabled=True)
# === Quick Demo: Cascade / Construction ===
industry = (st.session_state.get("industry") or "").lower()
industry = (st.session_state.get("industry") or "").lower()

# Optional – only if you really need `ge` later:
ge = None
try:
    proj_type = (
        st.session_state.get("project_type")
        or st.session_state.get("pm_project_type")
        or st.session_state.get("ge_proj_type")
        or ("well" if industry in ("oil_gas", "green_energy") else "building")
    )
    ge = _ge_config(industry, proj_type)
except Exception:
    # Swallow errors so the quick demo keeps working
    ge = None


if industry in ("oil_gas", "green_energy"):
    colW1, colW2 = st.columns(2)
    with colW1:
        if st.button("Seed Well Plan (Draft)"):
            save_artifact(PROJECT_ID, PHASE_ID, "Wells", "Well_Plan", {
                "wells": ["W1","W2"], "drill_sequence": ["W1","W2"], "constraints": {"rigs": 1}
            })
    with colW2:
        if st.button("Approve Latest Well Plan (Trigger Requests)"):
            latest_wp = get_latest(PROJECT_ID, "Well_Plan", PHASE_ID)
            if latest_wp:
                approve_artifact(PROJECT_ID, latest_wp["artifact_id"])
                st.toast("Well Plan approved (manual mode: no auto downstream).")
                drain_events(PROJECT_ID)




# else: no quick demo for other industries (leave blank for now)

# =============================================================================
# Render selected hub (Rev3 page content) — only when not in Modules
# =============================================================================

    if st.session_state.mode == "projects":
        st.session_state["__pm_overview_doc_key"] = "projects_overview"
    # --- Simple override: Ops Call Center goes to our local module
    if st.session_state.mode == "ops" and st.session_state.ops_mode == "call_center":
        try:
            mod = __import__("ops_call_center", fromlist=["run"])
            data = mod.run(T={"ops_mode": "call_center"})
            # Keep autosave working as usual
            if st.session_state.mode == "projects":
                st.session_state["__pm_overview_doc_key"] = "projects_overview"
            else:
                st.session_state["__pm_overview_doc_key"] = "ops_overview_call_center"
        except Exception as e:
            st.error(f"Call Center module error: {e}")
        # Don't render the default hub below
        st.stop()

# =============================================================================
# Autosave engine (runs after render)
# =============================================================================
ns = f"{industry}:ops:{st.session_state.ops_mode}" if st.session_state.mode == "ops" else f"{industry}:projects"
doc_key_current = st.session_state.get(f"doc_key_{ns}", f"{industry}_{st.session_state.mode}")
autosave_enabled = st.session_state.get(f"autosave_{ns}", False)

if autosave_enabled and st.session_state.get("active_project_id"):
    try:
        snap = json.dumps(data, sort_keys=True, default=str)
        fingerprint = hashlib.md5(snap.encode("utf-8")).hexdigest()
        last_key = f"last_snapshot__{ns}__{doc_key_current}"
        if st.session_state.get(last_key) != fingerprint:
            status = save_project_doc(username, ns, st.session_state.active_project_id, doc_key_current, data)
            try:
                if st.session_state.mode == "projects":
                    hist_key = (st.session_state.get("__pm_overview_doc_key") or doc_key_current)
                else:
                    hist_key = f"ops_overview_{st.session_state.ops_mode}"
                append_snapshot(username, ns, st.session_state.active_project_id, hist_key, data)
            except Exception:
                pass
            st.session_state[last_key] = fingerprint
            st.caption(f"Autosaved ({status.get('mode','local')}).")
    except Exception:
        pass

# =============================================================================
# =============================================================================
# FEL Governance & Stage Control (projects-only)
