# workflows/pm_hub_government.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import importlib, inspect
import streamlit as st

from services.pm_bridge import load_stage
from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel

MODULE_ALIASES: Dict[str, str] = {
    # FEL1 (Screening / Strategic Outline)
    "workflows.modules.problem_statement":        "workflows.pm_gov.problem_statement",
    "workflows.modules.option_screening":         "workflows.pm_gov.option_screening",
    "workflows.modules.site_location_screener":   "workflows.pm_gov.site_location_screener",
    "workflows.modules.stakeholder_benefits_map": "workflows.pm_gov.stakeholder_benefits_map",
    "workflows.modules.high_level_cba":           "workflows.pm_gov.high_level_cba",

    # FEL2 (Outline Business Case / Concept)
    "workflows.modules.conops_requirements":      "workflows.pm_gov.conops_requirements",
    "workflows.modules.preliminary_schedule":     "workflows.pm_gov.preliminary_schedule",
    "workflows.modules.rom_economics_gov":        "workflows.pm_gov.rom_economics",
    "workflows.modules.procurement_strategy":     "workflows.pm_gov.procurement_strategy",

    # FEL3 (Full Business Case / Definition)
    "workflows.modules.detailed_requirements":    "workflows.pm_gov.detailed_requirements",
    "workflows.modules.cost_model":               "workflows.pm_gov.cost_model",
    "workflows.modules.risk_register":            "workflows.pm_gov.risk_register",
    "workflows.modules.l2l3_schedule_gov":        "workflows.pm_gov.l2l3_schedule",

    # FEL4 (Delivery & Handover)
    "workflows.modules.delivery_dashboard":       "workflows.pm_gov.delivery_dashboard",
    "workflows.modules.readiness_acceptance":     "workflows.pm_gov.readiness_acceptance",
    "workflows.modules.handover_asbuilt_benefits": "workflows.pm_gov.handover_asbuilt_benefits",
}

STAGES = {
    "fel1": {
        "label": "Screening / Strategic Outline",
        "cards": [
            ("Problem / Needs Statement", "workflows.modules.problem_statement"),
            ("Option Screening", "workflows.modules.option_screening"),
            ("Site / Location Screener", "workflows.modules.site_location_screener"),
            ("Stakeholder & Benefits Map", "workflows.modules.stakeholder_benefits_map"),
            ("High-level CBA", "workflows.modules.high_level_cba"),
        ],
        "gate": ["Need validated", "Options shortlist", "Stakeholders mapped", "CBA draft"],
    },
    "fel2": {
        "label": "Outline Business Case / Concept",
        "cards": [
            ("CONOPS & Requirements (Draft)", "workflows.modules.conops_requirements"),
            ("Preliminary Schedule", "workflows.modules.preliminary_schedule"),
            ("ROM Economics", "workflows.modules.rom_economics_gov"),
            ("Procurement Strategy (Outline)", "workflows.modules.procurement_strategy"),
        ],
        "gate": ["CONOPS draft", "ROM ±30%", "Prelim schedule"],
    },
    "fel3": {
        "label": "Full Business Case / Definition",
        "cards": [
            ("Detailed Requirements Baseline", "workflows.modules.detailed_requirements"),
            ("Cost Model (CAPEX/OPEX)", "workflows.modules.cost_model"),
            ("Risk Register (quantified)", "workflows.modules.risk_register"),
            ("L2/L3 Schedule", "workflows.modules.l2l3_schedule_gov"),
        ],
        "gate": ["Reqs baseline", "Cost confidence", "Risks quantified", "L2/L3 issued"],
    },
    "fel4": {
        "label": "Delivery & Handover",
        "cards": [
            ("Delivery Dashboard", "workflows.modules.delivery_dashboard"),
            ("Readiness / Acceptance", "workflows.modules.readiness_acceptance"),
            ("Handover / As-built & Benefits", "workflows.modules.handover_asbuilt_benefits"),
        ],
        "gate": ["Readiness OK", "Acceptance signed", "Benefits tracking live"],
    },
}

# --- Module resolution helpers (same pattern as Aerospace) ---
def _candidates(alias: str):
    real = MODULE_ALIASES.get(alias)
    return [real, alias] if real else [alias]


def _import_first(paths):
    import importlib
    for p in paths:
        try:
            mod = importlib.import_module(p)
            return mod, p
        except Exception:
            continue
    return None, None


def _has_run(mod) -> bool:
    import inspect
    return hasattr(mod, "run") and inspect.isfunction(getattr(mod, "run"))


def safe_launch(alias: str, key_prefix: str):
    mod, resolved = _import_first(_candidates(alias))
    if not mod:
        st.error(f"Module not found: {alias}")
        return
    if not _has_run(mod):
        st.error(f"No run() in {resolved}")
        return
    try:
        mod.run(key=key_prefix)
    except TypeError:
        mod.run()


def render(T=None):
    st.header("Government — PM Hub")
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()
    stage_key = st.radio(
        "Stage",
        list(STAGES.keys()),
        format_func=lambda k: f"{k.upper()} – {STAGES[k]['label']}",
        horizontal=True,
        key="gov_stage_radio",
    )

    with st.expander("Gate checklist", expanded=False):
        cols = st.columns(3)
        for i, item in enumerate(STAGES[stage_key]["gate"]):
            with cols[i % 3]:
                st.checkbox(item, key=f"gov_gate_{stage_key}_{i}")

    for title, alias in STAGES[stage_key]["cards"]:
        st.markdown(f"### {title}")
        if st.button(f"Open · {title}", key=f"gov_{stage_key}_{alias}_open"):
            safe_launch(alias, key_prefix=f"gov_{stage_key}_{alias}")

    with st.expander("Engineering (common)"):
        st.info("Hook shared engineering tools here if needed.")
        st.json({"fel1": load_stage("fel1").get("payload", {}),
                 "fel2": load_stage("fel2").get("payload", {}),
                 "fel3": load_stage("fel3").get("payload", {})}, expanded=False)

    with st.expander("Debug — module resolution", expanded=False):
        for k, v in MODULE_ALIASES.items():
            mod, resolved = _import_first(_candidates(k))
            has = _has_run(mod) if mod else False
            st.write({"alias": k, "resolved": resolved, "has_run": bool(has)})