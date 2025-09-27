# services/registry.py
from typing import List, Dict, TypedDict
def load_registry(industry: str, phase: str):
    import streamlit as st
    return st.session_state.get("artifact_registry", {}).get((industry, phase), {})

class Card(TypedDict):
    title: str
    description: str
    module_path: str
    entry: str  # usually "run"

def _exists(module_path: str, entry: str) -> bool:
    try:
        mod = __import__(module_path, fromlist=[entry])
        getattr(mod, entry)
        return True
    except Exception:
        return False

def filter_available(cards: List[Card]) -> List[Card]:
    return [c for c in cards if _exists(c["module_path"], c["entry"])]

# ===== Manufacturing-specific FEL cards =====

def _card(module_path: str, entry: str, title: str, description: str) -> Card:
    return {"title": title, "description": description, "module_path": module_path, "entry": entry}

FEL_CARDS_MFG = {
    "FEL1": [  # Screening
        _card("workflows.pm_mfg.business_case_factory", "run",
              "Business Case — Factory Program",
              "Demand, mix, takt, ROM CAPEX/OPEX, quick economics."),
        _card("workflows.pm_mfg.demand_forecast", "run",
              "Demand & Mix Forecast",
              "Volume scenarios by model with ramps/seasonality."),
    ],
    "FEL2": [  # Pre-FEED
        _card("workflows.pm_mfg.footprint_sizer", "run",
              "Footprint & Layout Sizer",
              "Lines/cells/warehouse → net/gross floor & site acres."),
        _card("workflows.pm_mfg.site_selector", "run",
              "Site Selector",
              "Score candidate locations: labor/logistics/incentives/risk."),
        _card("workflows.pm_mfg.eng_concept", "run",
              "Engineering Concept (notes)",
              "Concept layout & utilities basis."),
    ],
    "FEL3": [  # FEED
        _card("workflows.pm_mfg.schedule_developer_mfg", "run",
              "Schedule Developer (L2/L3)",
              "Phasing, long-leads, critical path."),
        _card("workflows.pm_mfg.capex_opex_estimator", "run",
              "CAPEX/OPEX Estimator (Class 3)",
              "Parametric estimate for equipment/building/utilities."),
    ],
    "FEL4": [  # Execution & Detail Design
        _card("workflows.pm_mfg.procurement_packages", "run",
              "Procurement Packages",
              "Bid packages and long-lead orders."),
        _card("workflows.pm_mfg.construction_plan", "run",
              "Construction Plan",
              "Exec plan, interfaces, and HSE."),
        _card("workflows.pm_mfg.commissioning_plan", "run",
              "Commissioning Plan",
              "RFSU/OR milestones and readiness."),
    ],
}

def get_fel_cards_for(industry: str) -> Dict[str, List[Card]]:
    return FEL_CARDS_MFG if str(industry).lower() == "manufacturing" else FEL_CARDS

# ------- OPS cards mapped to your Rev3 names -------
OPS_CARDS: Dict[str, List[Card]] = {
    "daily_ops": [
        {
            "title": "Andon Incident Log",
            "description": "Capture line stops, downtime, root causes and countermeasures; see KPIs and charts.",
            "module": "workflows.tools.andon_log",
            "icon": "🚨",
            "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]},
        },
        {
            "title": "Ops One-Pager (PDF)",
            "description": "Generate a one-page PDF/TXT of current Ops KPIs from the consolidated snapshot.",
            "module": "workflows.tools.ops_one_pager",
            "icon": "🖨️",
            "tags": {"industries": ["manufacturing"], "subcats": ["all"]},
        },
        {
            "title": "Shift Huddle Board",
            "description": "Daily stand-up: top priorities, issues, owners, and due dates.",
            "module": "workflows.tools.shift_huddle",
            "icon": "🧭",
            "tags": {"industries": ["manufacturing"], "subcats": ["all"]},
        },
        {
            "title": "CMMS (Lite) — Work Orders",
            "description": "Track PM/CM work orders, priorities, due/complete dates, and effort minutes.",
            "module": "workflows.tools.cmms_lite",
            "icon": "🛠️",
            "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]},
        },
        {
            "title": "SPC Monitor (Lite)",
            "description": "Enter samples, set LSL/USL, see yield by station and a quick trend.",
            "module": "workflows.tools.spc_monitor",
            "icon": "📈",
            "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]},
        },
        {
            "title": "OEE Board",
            "description": "Availability / Performance / Quality with downtime pulled from Andon automatically.",
            "module": "workflows.tools.oee_board",
            "icon": "📊",
            "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]},
        },
        {
            "title": "SMT Feeder Setup Tracker",
            "description": "Track feeder setup/teardown times, missing reels, kit readiness, and operator notes.",
            "module": "workflows.tools.smt_feeder_setup",
            "icon": "🧰",
            "tags": {"industries": ["manufacturing"], "subcats": ["electronics"]},
        },
        {
            "title": "First-Pass Yield (FPY)",
            "description": "Record tests/failures by station and line; see FPY by station and overall.",
            "module": "workflows.tools.fpy_dashboard",
            "icon": "🎯",
            "tags": {"industries": ["manufacturing"], "subcats": ["electronics"]},
        },
        {
            "title": "OTIF Tracker",
            "description": "On-Time-In-Full for inbound/outbound orders; partner view and reasons.",
            "module": "workflows.tools.otif_tracker",
            "icon": "🚚",
            "tags": {"industries": ["manufacturing"], "subcats": ["supply_chain"]},
        },
        {
            "title": "Kanban Replenishment",
            "description": "Min/Max cards, on hand vs in transit, triggers and recommended order quantity.",
            "module": "workflows.tools.kanban_replenishment",
            "icon": "📦",
            "tags": {"industries": ["manufacturing"], "subcats": ["supply_chain"]},
        },

        # If you keep these legacy module_path cards, scope them too:
        {"title": "Uptime / Power Demand", "description": "Track availability and demand.",
         "module_path": "modules.power_demand", "entry": "run",
         "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]}},
        {"title": "Incident Log (HSE)", "description": "Capture incidents and actions.",
         "module_path": "modules.standup_notes", "entry": "run",
         "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]}},
        {"title": "Stream Calculator", "description": "Quick production/stream checks.",
         "module_path": "modules.stream_calculator", "entry": "stream_calculator",
         "tags": {"industries": ["manufacturing"], "subcats": ["automotive", "electronics"]}},
    ],
    # ...


    "small_projects": [
        {
            "title": "SMED Changeover Reduction",
            "description": "Analyze changeover tasks, apply ECRS, and generate an action plan to cut setup times.",
            "module": "workflows.tools.smed_changeover",   # <-- use 'module' not 'module_path'
            "icon": "⏱️",
        },
        {
            "title": "Kaizen Tracker",
            "description": "Capture ideas, screen, run trials, standardize, and track ROI/payback.",
            "module": "workflows.tools.kaizen_tracker",
            "icon": "🧩",
        },

        {
            "title": "Mini Scope Builder",
            "description": "Define scope/WBS for small changes.",
            "module": "workflows.tools.mini_scope_builder",
            "icon": "📝",
            "tags": {"subcats": ["all"]},
        },
        {
            "title": "Lightweight Schedule",
            "description": "Quick plan for short jobs.",
            "module": "workflows.tools.lightweight_schedule",
            "icon": "🗓️",
            "tags": {"subcats": ["all"]},
        },
        {
            "title": "Milk-Run Route Builder",
            "description": "Plan supplier pickup loop: stops, dwell, loads, capacity & total route time.",
            "module": "workflows.tools.milk_run_builder",
            "icon": "🗺️",
            "tags": {"subcats": ["supply_chain"]},
        },
        {
            "title": "Supplier Development A3 (Mini)",
            "description": "Capture problem → analysis → countermeasures; track OTD/PPM/Lead-time.",
            "module": "workflows.tools.supplier_dev_a3",
            "icon": "🧾",
            "tags": {"subcats": ["supply_chain"]},
        },

        {
            "title": "Risk (Lite)",
            "description": "Budget + simple risk for small work.",
            "module": "workflows.tools.risk_lite",
            "icon": "⚠️",
            "tags": {"subcats": ["all"]},
        },
    ],
}
# Legacy compatibility for Ops hubs that import OPS_TOOLS
# Map it to the same structure you already keep in OPS_CARDS.
OPS_TOOLS = OPS_CARDS
# --- Manufacturing small projects tools ---
OPS_TOOLS.setdefault("small_projects", [])

_smed_card = {
    "title": "SMED Changeover Reduction",
    "description": "Analyze changeover tasks, apply ECRS, and generate an action plan to cut setup times.",
    "module": "workflows.tools.smed_changeover",
    "icon": "⏱️",
}

if not any(c.get("module") == _smed_card["module"] for c in OPS_TOOLS["small_projects"]):
    OPS_TOOLS["small_projects"].append(_smed_card)

# ===== Exported Registry Functions =====

def get_latest(industry: str, phase: str):
    import streamlit as st
    return st.session_state.get("artifact_registry", {}).get((industry, phase), {})
