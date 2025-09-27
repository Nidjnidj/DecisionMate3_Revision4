import streamlit as st

def required_artifacts_for_phase(phase_code: str):
    # Replace with your actual logic or import if needed
    # Example:
    # return ["WBS", "Schedule", "Cost Estimate"]
    pass

def artifact_status_summary(phase_code: str):
    """
    Summarize approval status for the current phase.
    Works whether required_artifacts_for_phase returns a list of dicts
    ({'workstream','type'}) or plain strings.
    """
    required = required_artifacts_for_phase(phase_code) or []

    arts = st.session_state.get("artifacts", {})

    # Normalize required types to plain strings
    req_types = []
    for r in required:
        if isinstance(r, dict):
            req_types.append(r.get("type") or r.get("name") or str(r))
        else:
            req_types.append(str(r))

    done = [t for t in req_types if arts.get(t) == "Approved"]
    pend = [t for t in req_types if arts.get(t) in ("Pending", "Draft", "In Progress")]
    miss = [t for t in req_types if t not in arts]

    pct = int(100 * len(done) / max(1, len(req_types)))
    return pct, done, pend, miss