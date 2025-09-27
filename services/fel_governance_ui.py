import streamlit as st
from services.fel_governance import (
    STAGE_DEFAULT_DELIVERABLES,
    REQUIRED_ARTIFACTS_STAGE,
    ensure_stage_default_deliverables,
)

def render_fel_governance():
    # (optional) ensure these exist only when needed
    if "team_members" not in st.session_state:
        st.session_state.team_members = {"Subsurface": [], "Engineering": [], "Cost": [], "Schedule": [], "Risk": []}
    if "reviewers" not in st.session_state: st.session_state.reviewers = []
    if "approvers" not in st.session_state: st.session_state.approvers = []
    if "deliverables" not in st.session_state:
        st.session_state.deliverables = {"FEL1": [], "FEL2": [], "FEL3": [], "FEL4": []}
    if "artifacts" not in st.session_state: st.session_state.artifacts = {}
    with st.expander("FEL Governance & Stage Control", expanded=True):
        st.write(f"**Current FEL Stage:** {st.session_state.fel_stage}")

        # Team Member Assignment
        st.subheader("Assign Team Members")
        cols_team = st.columns(5)
        roles = list(st.session_state.team_members.keys())
        for i, role in enumerate(roles):
            with cols_team[i]:
                emails = st.text_area(f"{role} Team", value=", ".join(st.session_state.team_members[role]), key=f"team_{role}")
                st.session_state.team_members[role] = [e.strip() for e in emails.split(",") if e.strip()]

        # Reviewers & Approvers
        st.subheader("Reviewers & Approvers")
        reviewers = st.text_area("Reviewer Emails", value=", ".join(st.session_state.reviewers))
        st.session_state.reviewers = [e.strip() for e in reviewers.split(",") if e.strip()]
        approvers = st.text_area("Approver Emails", value=", ".join(st.session_state.approvers))
        st.session_state.approvers = [e.strip() for e in approvers.split(",") if e.strip()]

        # Deliverables
        st.subheader(f"Deliverables for {st.session_state.fel_stage}")
        ensure_stage_default_deliverables(st.session_state.fel_stage, st.session_state)
        col_d1, col_d2 = st.columns([3,1])
        with col_d1:
            new_deliv = st.text_input("Add Deliverable")
        with col_d2:
            if st.button("Reset to Stage Defaults"):
                st.session_state.deliverables[st.session_state.fel_stage] = [
                    {"name": n, "status": "In Progress"} for n in STAGE_DEFAULT_DELIVERABLES.get(st.session_state.fel_stage, [])
                ]
        if st.button("Add Deliverable") and new_deliv:
            st.session_state.deliverables[st.session_state.fel_stage].append({"name": new_deliv, "status": "In Progress"})

        for i, d in enumerate(st.session_state.deliverables[st.session_state.fel_stage]):
            col1, col2 = st.columns([3,1])
            with col1: st.write(d["name"])
            with col2:
                new_status = st.selectbox("Status", ["In Progress", "Done"], index=0 if d["status"] == "In Progress" else 1, key=f"deliv_{i}")
                st.session_state.deliverables[st.session_state.fel_stage][i]["status"] = new_status

        # Artifact Status (stage-specific)
        st.subheader(f"Artifacts for {st.session_state.fel_stage}")
        for art in REQUIRED_ARTIFACTS_STAGE[st.session_state.fel_stage]:
            current = st.session_state.artifacts.get(art, "Not Started")
            idx = {"Not Started":0, "In Progress":1, "Approved":2}.get(current, 0)
            status = st.selectbox(f"{art}", ["Not Started", "In Progress", "Approved"], index=idx, key=f"art_{art}")
            st.session_state.artifacts[art] = status

        # Gate Approval Logic
        def can_move_stage():
            arts_ok = all(st.session_state.artifacts.get(a) == "Approved" for a in REQUIRED_ARTIFACTS_STAGE[st.session_state.fel_stage])
            deliv_ok = all(d["status"] == "Done" for d in st.session_state.deliverables[st.session_state.fel_stage])
            rev_ok = len(st.session_state.reviewers) > 0
            appr_ok = len(st.session_state.approvers) > 0
            return arts_ok and deliv_ok and rev_ok and appr_ok

        approver_email = st.text_input("Approver Email for Gate Move")
        if st.button("Approve Gate & Move to Next FEL"):
            if approver_email in st.session_state.approvers:
                if can_move_stage():
                    if st.session_state.fel_stage == "FEL1":
                        st.session_state.fel_stage = "FEL2"
                    elif st.session_state.fel_stage == "FEL2":
                        st.session_state.fel_stage = "FEL3"
                    elif st.session_state.fel_stage == "FEL3":
                        st.session_state.fel_stage = "FEL4"
                    else:
                        st.success("Project is now in Execution / FEL4 — no further stages.")
                    st.success(f"Gate approved. Moved to {st.session_state.fel_stage}.")
                else:
                    st.error("Not all requirements met to move stage.")
            else:
                st.error("Approver email not in approvers list.")