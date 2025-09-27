import streamlit as st

STATUS_COLORS = {
    "Missing":  "#9AA0A6",
    "Pending":  "#F2C94C",
    "Draft":    "#F2994A",
    "Approved": "#27AE60",
}

def artifact_status_label(art):
    if not art: return "Missing"
    return art.get("status", "Draft")

def progress_bar(pct):
    st.progress(min(max(pct, 0), 100), text=f"{pct}% of required artifacts approved")

def right_rail_gate(phase_code, artifact_status_summary_func, session_state):
    st.markdown("### Gate Check")
    pct, done, pend, miss = artifact_status_summary_func(phase_code)
    if miss:
        st.error("Missing artifacts:\n\n- " + "\n- ".join(miss))
    if pend:
        st.warning("Not approved yet:\n\n- " + "\n- ".join(f"{a} (status: {session_state.get('artifacts',{}).get(a,'?')})" for a in pend))
    if done and not miss and not pend:
        st.success("All required artifacts approved for this gate.")