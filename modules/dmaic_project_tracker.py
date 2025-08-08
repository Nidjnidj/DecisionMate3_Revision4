import streamlit as st

def run(T):
    st.title("📈 DMAIC Project Tracker")

    st.markdown("""
    Use this tool to track the progress of your Six Sigma project through each of the DMAIC phases.
    """)

    phases = ["Define", "Measure", "Analyze", "Improve", "Control"]
    status_options = ["Not Started", "In Progress", "Completed"]
    notes = {}

    for phase in phases:
        with st.expander(f"🔹 {phase} Phase"):
            status = st.selectbox(f"Status for {phase}", status_options, key=f"{phase}_status")
            note = st.text_area(f"Notes for {phase}", key=f"{phase}_notes")
            notes[phase] = {"status": status, "note": note}

    if st.button("📤 Save Project Status"):
        st.success("✅ Project status saved (this is a demo — connect Firebase for persistence).")

    st.markdown("---")
    st.markdown("🔍 *DMAIC: Define, Measure, Analyze, Improve, Control — the backbone of Six Sigma methodology.*")
