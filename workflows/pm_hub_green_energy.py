# workflows/pm_hub_green_energy.py
from __future__ import annotations
import streamlit as st

from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel

from services.kpis import compute_pm_kpis
from services.overview import render_pm_overview


def render() -> None:
    st.subheader("🌱 PM Hub — Green Energy")

    # KPI snapshot (optional)
    with st.sidebar.expander("📁 Project Data (Green)", expanded=True):
        capex = st.number_input("CAPEX (M$)", min_value=0.0, value=20.0)
        opex = st.number_input("OPEX (M$/y)", min_value=0.0, value=1.0)
        duration = st.number_input("Schedule (months)", min_value=0.0, value=18.0)
        risk = st.slider("Risk Index", 0.0, 10.0, 3.0)
    _ = compute_pm_kpis({"capex": capex, "opex": opex, "schedule_months": duration, "risk_score": risk})

    # Cross-industry panels
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()
    st.markdown("---")

    # Green energy pipeline (simple placeholders)
    st.markdown("### Green Project Stages")
    st.caption("Typical: Site → Interconnection → Permitting → EPC → COD")
    stage = st.radio(
        "Stage",
        ["Site", "Interconnection", "Permitting", "EPC", "COD"],
        horizontal=True,
    )

    if stage == "Site":
        st.info("Add site selection, wind/solar resource, layout, land control.")
    elif stage == "Interconnection":
        st.info("Add queue status, studies, upgrades, preferred POI.")
    elif stage == "Permitting":
        st.info("Add environmental & local permitting tracker and risks.")
    elif stage == "EPC":
        st.info("Add EPC scope, schedule, CAPEX by WBS, and QA/QC plan.")
    elif stage == "COD":
        st.info("Add commissioning evidence, performance test, O&M handover.")

    with st.expander("Overview", expanded=False):
        render_pm_overview(
            {"capex": capex, "opex": opex, "schedule_months": duration, "risk_score": risk, "fel_stage": "N/A"}
        )
