# modules/it_engineering.py
from __future__ import annotations
import streamlit as st
from typing import List, Dict, Any
from utils.artifact_bridge import save_artifact, get_latest, approve_artifact
from modules.it_contracts import IT_BUSINESS_CASE, IT_ENGINEERING, EngineeringDesignIT

def _team_editor(default: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    st.markdown("**Team setup** (role, count)")
    default = default or [{"role":"Product Manager","count":1},{"role":"Backend Dev","count":2},{"role":"Frontend Dev","count":2},{"role":"QA","count":1}]
    rows = st.number_input("How many roles?", min_value=1, value=len(default), step=1, key="it_eng_team_rows")
    out=[]
    for i in range(rows):
        with st.expander(f"Role #{i+1}", expanded=(i<2)):
            role = st.text_input("Role", value=(default[i]["role"] if i<len(default) else ""), key=f"it_eng_role_{i}")
            count = st.number_input("Count", min_value=0, value=(int(default[i]["count"]) if i<len(default) else 1), key=f"it_eng_cnt_{i}")
            out.append({"role":role,"count":count})
    return out

def _components_editor(default: List[Dict[str, str]] = None) -> List[Dict[str, str]]:
    st.markdown("**Key components** (name, type)")
    default = default or [{"name":"API Gateway","type":"service"},{"name":"Web App","type":"frontend"}]
    rows = st.number_input("How many components?", min_value=1, value=len(default), step=1, key="it_eng_comp_rows")
    out=[]
    for i in range(rows):
        with st.expander(f"Component #{i+1}", expanded=(i==0)):
            name = st.text_input("Name", value=(default[i]["name"] if i<len(default) else ""), key=f"it_eng_comp_name_{i}")
            ctype = st.text_input("Type", value=(default[i]["type"] if i<len(default) else ""), key=f"it_eng_comp_type_{i}")
            out.append({"name":name,"type":ctype})
    return out

def run():
    st.subheader("IT · Engineering")
    project_id = st.session_state.get("active_project_id", "demo-project")

    bc = get_latest(project_id, IT_BUSINESS_CASE)
    if not bc:
        st.warning("No Business Case found. Please complete and save the Business Case first.")
        return
    if not bc.get("approved"):
        st.warning("Business Case exists but is not Approved yet. Approve it before Engineering.")
        return

    st.info(f"Upstream Business Case: **{bc['data'].get('project_name','')}** · Selected option: **{bc['data'].get('selected_option','')}**")

    arch = st.selectbox("Architecture", ["Monolith","Microservices","Serverless"], index=1)
    comps = _components_editor()
    integrations = st.text_area("Integration points (one per line)", value="CRM\nPayments")
    nfrs = st.text_area("Non-functional requirements (one per line)", value="Availability 99.9%\nLatency < 200ms")
    team = _team_editor()
    sp = st.number_input("Backlog story points (total)", min_value=1, value=200, step=5)
    envs = st.multiselect("Environments", ["dev","test","staging","prod"], default=["dev","test","prod"])
    deps = st.text_area("Dependencies (one per line)", value="Billing contract\nSSO provider")
    risks = st.text_area("Risks (one per line)", value="Unknown legacy integration\nTeam turnover risk")

    if st.button("Save Engineering Design", type="primary"):
        data = EngineeringDesignIT(
            architecture_choice=arch,
            key_components=comps,
            integration_points=[s.strip() for s in integrations.splitlines() if s.strip()],
            nfrs=[s.strip() for s in nfrs.splitlines() if s.strip()],
            team_setup=team,
            backlog_story_points=int(sp),
            environments=envs,
            dependencies=[s.strip() for s in deps.splitlines() if s.strip()],
            risks=[s.strip() for s in risks.splitlines() if s.strip()],
            upstream_refs=[bc["id"], IT_BUSINESS_CASE],
        ).to_dict()
        rec = save_artifact(project_id, IT_ENGINEERING, data, stage="Engineering")
        st.success(f"Saved Engineering Design (id: {rec['id']}).")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Approve Engineering ✅"):
            if approve_artifact(project_id, IT_ENGINEERING):
                st.success("Engineering approved.")
            else:
                st.warning("Nothing to approve yet.")
    with c2:
        st.info("Next: IT · Schedule")
