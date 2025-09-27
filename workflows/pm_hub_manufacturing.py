# workflows/pm_hub_manufacturing.py
from __future__ import annotations

import importlib
from types import ModuleType
import streamlit as st
from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel
# -----------------------------
# where your actual tools live:
#   workflows/pm_mfg/*.py
# -----------------------------
MODULE_ALIASES = {
    # FEL1 – Screening
    "workflows.modules.business_case_factory": "workflows.pm_mfg.business_case_factory",
    "workflows.modules.option_screening":      "workflows.pm_mfg.option_screening",
    "workflows.modules.site_screener":         "workflows.pm_mfg.site_selector",
    "workflows.modules.market_volume_scenarios": "workflows.pm_mfg.market_volume_scenarios",

    # FEL2 – Pre-FEED (Concept)
    "workflows.modules.line_designer_lite":       "workflows.pm_mfg.eng_concept",
    "workflows.modules.throughput_simulator_lite":"workflows.pm_mfg.line_simulator",
    "workflows.modules.footprint_sizer":          "workflows.pm_mfg.footprint_sizer",
    "workflows.modules.rom_economics":            "workflows.pm_mfg.capex_opex_estimator",

    # FEL3 – FEED (Definition)
    "workflows.modules.layout_planner":       "workflows.pm_mfg.construction_plan",
    "workflows.modules.opex_model":           "workflows.pm_mfg.capex_opex_estimator",
    "workflows.modules.capacity_shift_plan":  "workflows.pm_mfg.demand_forecast",
    "workflows.modules.l2l3_schedule":        "workflows.pm_mfg.schedule_developer_mfg",

    # FEL4 – Execution & Detail Design
    "workflows.modules.execution_dashboard":      "workflows.pm_mfg.procurement_packages",
    "workflows.modules.commissioning_readiness":  "workflows.pm_mfg.commissioning_plan",
    "workflows.modules.handover_asbuilt":         "workflows.pm_mfg.program_brief",
}

def _candidates(module_path: str) -> list[str]:
    """
    Return import candidates in order:
      1) alias to your pm_mfg module (if mapped)
      2) the exact path as passed
      3) generic pm_mfg/<name> fallback
      4) generic modules/<name> fallback
    """
    name = module_path.split(".")[-1]
    out: list[str] = []
    if module_path in MODULE_ALIASES:
        out.append(MODULE_ALIASES[module_path])
    out.append(module_path)
    # fallbacks (harmless if missing)
    pm_mfg = f"workflows.pm_mfg.{name}"
    modules = f"workflows.modules.{name}"
    if pm_mfg not in out:
        out.append(pm_mfg)
    if modules not in out:
        out.append(modules)
    # de-dup while preserving order
    seen, ordered = set(), []
    for p in out:
        if p not in seen:
            ordered.append(p)
            seen.add(p)
    return ordered

def _import_first(cands: list[str], entry: str) -> tuple[ModuleType, callable]:
    last_err = None
    for mp in cands:
        try:
            mod = importlib.import_module(mp)
            fn = getattr(mod, entry)
            return mod, fn
        except Exception as e:
            last_err = e
            continue
    raise last_err or ImportError(f"Could not import any of: {', '.join(cands)}")

def safe_launch(module_path: str, entry: str, label: str, key: str):
    cands = _candidates(module_path)
    try:
        _, fn = _import_first(cands, entry)
        if st.button(label, key=key):
            fn()
    except Exception as e:
        st.button(label, key=key, disabled=True)
        st.warning(f"Module not available yet for `{label}`. Tried: {', '.join(cands)}. Details: {e}")

# -----------------------------------------------------------------------------
# Page
# -----------------------------------------------------------------------------
SUBTYPES = ["Automotive plant"]  # extend later if needed

def _gate_checklist(prefix: str):
    cols = st.columns(5)
    with cols[0]:
        st.checkbox("Business case", key=f"{prefix}_gate_bc")
    with cols[1]:
        st.checkbox("Engineering", key=f"{prefix}_gate_eng")
    with cols[2]:
        st.checkbox("Economics", key=f"{prefix}_gate_econ")
    with cols[3]:
        st.checkbox("Schedule", key=f"{prefix}_gate_sch")
    with cols[4]:
        st.checkbox("Risk", key=f"{prefix}_gate_risk")

def _fel1():
    st.subheader("FEL1 — Screening")
    st.caption("Identify the business case, high-level scenarios and screen options. Output: go/no-go to Pre-FEED.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Business Case — Factory Program**")
        st.caption("Demand → volume → product mix; rough staffing; outline economics.")
        safe_launch("workflows.modules.business_case_factory", "run",
                    "Open: Business Case — Factory Program", key="fel1_bc")

        st.markdown("---")
        st.markdown("**Site / Location Screener**")
        st.caption("Filter candidate regions by logistics, incentives, utilities & labor.")
        safe_launch("workflows.modules.site_screener", "run",
                    "Open: Site / Location Screener", key="fel1_site")

    with c2:
        st.markdown("**Option Screening**")
        st.caption("Compare 2–4 factory options on key drivers (capex/opex/footprint/lead-time).")
        safe_launch("workflows.modules.option_screening", "run",
                    "Open: Option Screening", key="fel1_opt")

        st.markdown("---")
        st.markdown("**Market / Volume Scenarios**")
        st.caption("S-curve adoption & demand scenarios feeding the business case.")
        safe_launch("workflows.modules.market_volume_scenarios", "run",
                    "Open: Market / Volume Scenarios", key="fel1_market")

    st.divider()
    st.caption("Gate readiness checklist")
    _gate_checklist("fel1")

def _fel2():
    st.subheader("FEL2 — Pre-FEED (Concept)")
    st.caption("Develop the concept: flows, takt, preliminary layout, and ROM economics. Output: selected concept for FEED.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Line Designer (Lite)**")
        st.caption("Define steps, cycle times, buffers; basic balancing vs takt.")
        safe_launch("workflows.modules.line_designer_lite", "run",
                    "Open: Line Designer (Lite)", key="fel2_line")

        st.markdown("---")
        st.markdown("**Layout / Footprint Sizer**")
        st.caption("Rough equipment counts & aisle rules → area, bays and site footprint.")
        safe_launch("workflows.modules.footprint_sizer", "run",
                    "Open: Layout / Footprint Sizer", key="fel2_fp")

    with c2:
        st.markdown("**Throughput Simulator (Lite)**")
        st.caption("Simple discrete-event approximation to see bottlenecks and WIP.")
        safe_launch("workflows.modules.throughput_simulator_lite", "run",
                    "Open: Throughput Simulator (Lite)", key="fel2_sim")

        st.markdown("---")
        st.markdown("**ROM Economics**")
        st.caption("Rough-order CAPEX/OPEX & payback for the concept.")
        safe_launch("workflows.modules.rom_economics", "run",
                    "Open: ROM Economics", key="fel2_rom")

    st.divider()
    st.caption("Gate readiness checklist")
    _gate_checklist("fel2")

def _fel3():
    st.subheader("FEL3 — FEED (Definition)")
    st.caption("Lock definition: detailed layout, utilities sizing, capacity & shift plan, OPEX model, and L2/L3 schedule.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Detailed Layout Planner**")
        safe_launch("workflows.modules.layout_planner", "run",
                    "Open: Detailed Layout Planner", key="fel3_layout")

        st.markdown("---")
        st.markdown("**OPEX Model**")
        safe_launch("workflows.modules.opex_model", "run",
                    "Open: OPEX Model", key="fel3_opex")

    with c2:
        st.markdown("**Capacity / Shift Plan**")
        safe_launch("workflows.modules.capacity_shift_plan", "run",
                    "Open: Capacity / Shift Plan", key="fel3_cap")

        st.markdown("---")
        st.markdown("**L2/L3 Schedule**")
        safe_launch("workflows.modules.l2l3_schedule", "run",
                    "Open: L2/L3 Schedule", key="fel3_sched")

    st.divider()
    st.caption("Gate readiness checklist")
    _gate_checklist("fel3")

def _fel4():
    st.subheader("FEL4 — Execution & Detail Design")
    st.caption("Execute the plant: package tracking, vendor readiness, commissioning, and handover.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Execution Dashboard**")
        safe_launch("workflows.modules.execution_dashboard", "run",
                    "Open: Execution Dashboard", key="fel4_exec")

    with c2:
        st.markdown("**Commissioning Readiness**")
        safe_launch("workflows.modules.commissioning_readiness", "run",
                    "Open: Commissioning Readiness", key="fel4_comm")

    with c3:
        st.markdown("**Handover / As-built**")
        safe_launch("workflows.modules.handover_asbuilt", "run",
                    "Open: Handover / As-built", key="fel4_handover")

    st.divider()
    st.caption("Gate readiness checklist")
    _gate_checklist("fel4")

def render():
    st.header("PM Hub — Manufacturing")
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()
    st.caption("Lifecycle overlay: FEL1 Screening → FEL2 Pre-FEED → FEL3 FEED → FEL4 Execution & Detail Design.")

    # subtype (kept simple for now)
    st.selectbox("Manufacturing subtype", SUBTYPES, index=0, key="pm_mfg_subtype")

    stage = st.radio(
        "Stage",
        options=[
            "FEL1 — Screening",
            "FEL2 — Pre-FEED (Concept)",
            "FEL3 — FEED (Definition)",
            "FEL4 — Execution & Detail Design",
        ],
        horizontal=True,
        key="pm_mfg_stage",
    )

    st.write("")  # spacing

    if stage.startswith("FEL1"):
        _fel1()
    elif stage.startswith("FEL2"):
        _fel2()
    elif stage.startswith("FEL3"):
        _fel3()
    else:
        _fel4()
