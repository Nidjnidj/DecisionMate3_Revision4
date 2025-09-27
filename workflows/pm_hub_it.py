import streamlit as st
from services.kpis import compute_pm_kpis
from services.utils import go_to_module
# cross-industry panels
from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel


def render():
    st.subheader("💻 IT — PM Hub")

    # --- Cross-industry panels ---
    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()
    st.markdown("---")

    # --- IT-specific pipeline ---
    st.markdown("### IT · Pipeline (Business Case → Engineering → Schedule → Cost)")

    stage = st.radio("Stage", ["Business Case", "Engineering", "Schedule", "Cost"], horizontal=True)

    if stage == "Business Case":
        st.markdown("### IT · Business Case")
        project_name = st.text_input("Project name")
        business_owner = st.text_input("Business owner")
        problem = st.text_area("Problem statement")
        goals = st.text_area("Goals (one per line)")
        metrics_count = st.number_input("How many metrics?", min_value=1, max_value=5, value=1)

        for i in range(metrics_count):
            with st.expander(f"Metric #{i+1}"):
                name = st.text_input(f"Name", key=f"it_metric_name_{i}")
                target = st.text_input(f"Target", key=f"it_metric_target_{i}")
                unit = st.text_input(f"Unit", key=f"it_metric_unit_{i}")

    elif stage == "Engineering":
        st.info("Engineering stage — add IT architecture design, infrastructure planning, etc.")

    elif stage == "Schedule":
        st.info("Schedule stage — add project plan, milestones, dependencies.")

    elif stage == "Cost":
        st.info("Cost stage — add CAPEX / OPEX breakdown, ROI calculation.")
