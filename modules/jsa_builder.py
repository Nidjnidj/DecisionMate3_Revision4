import streamlit as st
import pandas as pd

def run(T):
    st.title("🛡️ Job Safety Analysis (JSA) Builder")

    st.markdown("""
    Use this form to create a JSA:  
    - Break the job into steps  
    - Identify hazards  
    - Define control measures
    """)

    if "jsa_table" not in st.session_state:
        st.session_state.jsa_table = []

    with st.form("jsa_form"):
        step = st.text_input("Job Step")
        hazard = st.text_input("Associated Hazard")
        control = st.text_input("Control Measure / PPE")
        submit = st.form_submit_button("➕ Add Step")

    if submit and step and hazard:
        st.session_state.jsa_table.append({
            "Step": step,
            "Hazard": hazard,
            "Control": control
        })

    if st.session_state.jsa_table:
        st.subheader("📋 JSA Table")
        df = pd.DataFrame(st.session_state.jsa_table)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download JSA Table", df.to_csv(index=False).encode("utf-8"), "jsa_table.csv")
    else:
        st.info("No job steps added yet.")
