# modules/it_business_case.py
from __future__ import annotations
import streamlit as st
from typing import List, Dict, Any
from utils.artifact_bridge import save_artifact, get_latest, approve_artifact
from modules.it_contracts import BusinessCaseIT, IT_BUSINESS_CASE

def _mlist(label: str, help_text: str = "", default: List[str] = None) -> List[str]:
    default = default or []
    txt = st.text_area(label, value="\n".join(default), help=help_text, height=120)
    return [line.strip() for line in txt.splitlines() if line.strip()]

def _metrics_editor(default: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    st.markdown("**Success metrics** (name, target, unit)")
    default = default or [{"name":"NPS","target":50,"unit":"score"}]
    rows = st.number_input("How many metrics?", min_value=1, value=len(default), step=1)
    out = []
    for i in range(rows):
        with st.expander(f"Metric #{i+1}", expanded=(i==0)):
            name = st.text_input("Name", value=(default[i]["name"] if i < len(default) else ""))
            target = st.number_input("Target", value=(default[i]["target"] if i < len(default) else 0.0))
            unit = st.text_input("Unit", value=(default[i]["unit"] if i < len(default) else ""))
            out.append({"name": name, "target": target, "unit": unit})
    return out

def _options_editor(default: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    st.markdown("**Delivery options**")
    default = default or [{
        "name":"Build in-house","description":"Internal team builds MVP.",
        "capex_est":10000.0,"opex_est":8000.0,"duration_months":3,"risk":"Resourcing"
    }]
    rows = st.number_input("How many options?", min_value=1, value=len(default), step=1)
    out = []
    for i in range(rows):
        with st.expander(f"Option #{i+1}", expanded=(i==0)):
            name = st.text_input("Name", value=(default[i]["name"] if i < len(default) else ""), key=f"opt_name_{i}")
            desc = st.text_area("Description", value=(default[i]["description"] if i < len(default) else ""), key=f"opt_desc_{i}")
            capex = st.number_input("CAPEX estimate (one-time)", value=(float(default[i]["capex_est"]) if i < len(default) else 0.0), key=f"opt_capex_{i}")
            opex = st.number_input("Monthly OPEX estimate", value=(float(default[i]["opex_est"]) if i < len(default) else 0.0), key=f"opt_opex_{i}")
            dur  = st.number_input("Duration (months)", min_value=1, value=(int(default[i]["duration_months"]) if i < len(default) else 1), key=f"opt_dur_{i}")
            risk = st.text_input("Key risk", value=(default[i]["risk"] if i < len(default) else ""), key=f"opt_risk_{i}")
            out.append({"name":name,"description":desc,"capex_est":capex,"opex_est":opex,"duration_months":dur,"risk":risk})
    return out

def run():
    st.subheader("IT · Business Case")
    project_id = st.session_state.get("active_project_id", "demo-project")

    latest = get_latest(project_id, IT_BUSINESS_CASE)
    default_bc = latest["data"] if latest else {}

    project_name = st.text_input("Project name", value=default_bc.get("project_name",""))
    business_owner = st.text_input("Business owner", value=default_bc.get("business_owner",""))
    problem_statement = st.text_area("Problem statement", value=default_bc.get("problem_statement",""))

    goals = _mlist("Goals (one per line)", default=default_bc.get("goals", ["Increase conversion","Reduce churn"]))
    metrics = _metrics_editor(default=default_bc.get("success_metrics"))
    options = _options_editor(default=default_bc.get("options"))
    opt_names = [o["name"] for o in options if o.get("name")]
    selected_option = st.selectbox("Selected option", opt_names, index=0 if opt_names else 0)

    assumptions = _mlist("Assumptions (one per line)", default=default_bc.get("assumptions", []))
    constraints = _mlist("Constraints (one per line)", default=default_bc.get("constraints", []))
    benefits = _mlist("Expected benefits (one per line)", default=default_bc.get("expected_benefits", []))

    if st.button("Save Business Case", type="primary"):
        if not project_name or not business_owner or not problem_statement or not selected_option:
            st.error("Please fill Project name, Business owner, Problem statement, and select an option.")
        else:
            bc = BusinessCaseIT(
                project_name=project_name,
                business_owner=business_owner,
                problem_statement=problem_statement,
                goals=goals,
                success_metrics=metrics,
                options=options,
                selected_option=selected_option,
                assumptions=assumptions,
                constraints=constraints,
                expected_benefits=benefits,
            )
            record = save_artifact(project_id, IT_BUSINESS_CASE, bc.to_dict(), stage="BusinessCase")
            st.success(f"Saved Business Case (id: {record['id']}).")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve Business Case ✅"):
            if approve_artifact(project_id, IT_BUSINESS_CASE):
                st.success("Business Case approved.")
            else:
                st.warning("Nothing to approve yet.")
    with col2:
        st.info("Next: IT · Engineering")
