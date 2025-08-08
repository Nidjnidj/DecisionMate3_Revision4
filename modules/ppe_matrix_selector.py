import streamlit as st

def run(T):
    st.title("🧤 PPE Matrix Selector")

    st.markdown("""
    Select a job activity or hazard environment to view recommended PPE.
    """)

    ppe_matrix = {
        "Welding": ["Helmet with face shield", "Welding gloves", "Flame-resistant clothing", "Safety boots"],
        "Chemical Handling": ["Chemical goggles", "Face shield", "Chemical-resistant gloves", "Apron"],
        "Working at Height": ["Harness with lanyard", "Helmet with chin strap", "Non-slip boots"],
        "Electrical Work": ["Insulated gloves", "Face shield", "Arc-rated clothing"],
        "Confined Space Entry": ["Tripod & harness", "Gas detector", "Helmet", "Respirator (if needed)"],
        "General Construction": ["Helmet", "Safety glasses", "Reflective vest", "Safety boots"]
    }

    job_type = st.selectbox("Select Activity or Hazard Type", list(ppe_matrix.keys()))

    if job_type:
        st.subheader("🧰 Recommended PPE:")
        for item in ppe_matrix[job_type]:
            st.markdown(f"- {item}")
