# workflows/pm_hub_aerospace.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import importlib, inspect
import streamlit as st

from services.pm_bridge import load_stage
from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel

# === Aliases → actual modules ===
MODULE_ALIASES: Dict[str, str] = {
    # FEL1 (SRR / Screening)
    "workflows.modules.program_brief":          "workflows.pm_aero.program_brief",
    "workflows.modules.option_screening":       "workflows.pm_aero.option_screening",
    "workflows.modules.site_capability_screener":"workflows.pm_aero.site_capability_screener",
    "workflows.modules.market_volume_scenarios": "workflows.pm_aero.market_volume_scenarios",

    # FEL2 (PDR / Concept)
    "workflows.modules.line_designer_lite":     "workflows.pm_aero.line_designer_lite",
    "workflows.modules.throughput_sim_lite":    "workflows.pm_aero.throughput_sim_lite",
    "workflows.modules.footprint_sizer":        "workflows.pm_aero.footprint_sizer",
    "workflows.modules.rom_economics":          "workflows.pm_aero.rom_economics",

    # FEL3 (CDR / Definition)
    "workflows.modules.detailed_layout_planner": "workflows.pm_aero.detailed_layout_planner",
    "workflows.modules.capacity_shift_plan":     "workflows.pm_aero.capacity_shift_plan",
    "workflows.modules.opex_model":              "workflows.pm_aero.opex_model",
    "workflows.modules.l2l3_schedule":           "workflows.pm_aero.l2l3_schedule",

    # FEL4 (FRR / Execution & Handover)
    "workflows.modules.execution_dashboard":     "workflows.pm_aero.execution_dashboard",
    "workflows.modules.qualification_readiness": "workflows.pm_aero.qualification_readiness",
    "workflows.modules.handover_asbuilt":        "workflows.pm_aero.handover_asbuilt",
}

STAGES = {
    "fel1": {
        "label": "SRR / Screening",
        "cards": [
            ("Business Case (Program Brief)", "workflows.modules.program_brief"),
            ("Option Screening (New vs MRO)", "workflows.modules.option_screening"),
            ("Site/Capability Screener", "workflows.modules.site_capability_screener"),
            ("Market/Volume Scenarios", "workflows.modules.market_volume_scenarios"),
        ],
        "gate": ["Program Brief", "Option shortlist", "Site shortlist", "Demand ranges"],
    },
    "fel2": {
        "label": "PDR / Concept",
        "cards": [
            ("Line Designer (Lite)", "workflows.modules.line_designer_lite"),
            ("Throughput Simulator (Lite)", "workflows.modules.throughput_sim_lite"),
            ("Footprint Sizer", "workflows.modules.footprint_sizer"),
            ("ROM Economics", "workflows.modules.rom_economics"),
        ],
        "gate": ["Stations/takt", "ROM ±30%", "Concept layout"],
    },
    "fel3": {
        "label": "CDR / Definition",
        "cards": [
            ("Detailed Layout Planner", "workflows.modules.detailed_layout_planner"),
            ("Capacity / Shift Plan", "workflows.modules.capacity_shift_plan"),
            ("OPEX Model", "workflows.modules.opex_model"),
            ("L2/L3 Schedule", "workflows.modules.l2l3_schedule"),
        ],
        "gate": ["Layout freeze", "Capacity basis", "OPEX basis", "L2/L3 issued"],
    },
    "fel4": {
        "label": "FRR / Execution & Handover",
        "cards": [
            ("Execution Dashboard", "workflows.modules.execution_dashboard"),
            ("Qualification & Commissioning Readiness", "workflows.modules.qualification_readiness"),
            ("Handover / As-built", "workflows.modules.handover_asbuilt"),
        ],
        "gate": ["Readiness OK", "Punchlist closed", "As-builts"],
    },
}

# --- Module resolution helpers ---
def _candidates(alias: str):
    real = MODULE_ALIASES.get(alias)
    return [real, alias] if real else [alias]


def _import_first(paths) -> Tuple[Optional[object], Optional[str]]:
    for p in paths:
        try:
            mod = importlib.import_module(p)
            return mod, p
        except Exception:
            continue
    return None, None


def _has_run(mod) -> bool:
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
        # Pass a unique key so st widgets do not collide across cards
        mod.run(key=key_prefix)
    except TypeError:
        mod.run()


# --- UI ---
def render(T=None):  # keep signature similar to other hubs
    st.header("Aerospace — PM Hub")
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()

    stage_key = st.radio(
        "Stage",
        list(STAGES.keys()),
        format_func=lambda k: f"{k.upper()} – {STAGES[k]['label']}",
        horizontal=True,
        key="aero_stage_radio",
    )

    # Gate checklist
    with st.expander("Gate checklist", expanded=False):
        cols = st.columns(3)
        for i, item in enumerate(STAGES[stage_key]["gate"]):
            with cols[i % 3]:
                st.checkbox(item, key=f"aero_gate_{stage_key}_{i}")

    # Cards
    for title, alias in STAGES[stage_key]["cards"]:
        st.markdown(f"### {title}")
        if st.button(f"Open · {title}", key=f"aero_{stage_key}_{alias}_open"):
            safe_launch(alias, key_prefix=f"aero_{stage_key}_{alias}")

    # Engineering (common)
    with st.expander("Engineering (common)"):
        st.info("Hook shared engineering tools here if needed.")
        st.json({"fel1": load_stage("fel1").get("payload", {}),
                 "fel2": load_stage("fel2").get("payload", {}),
                 "fel3": load_stage("fel3").get("payload", {})}, expanded=False)

    # Debug — module resolution
    with st.expander("Debug — module resolution", expanded=False):
        for k, v in MODULE_ALIASES.items():
            mod, resolved = _import_first(_candidates(k))
            has = _has_run(mod) if mod else False
            st.write({"alias": k, "resolved": resolved, "has_run": bool(has)})