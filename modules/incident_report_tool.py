import streamlit as st
import pandas as pd
from datetime import date

def run(T):
    st.title("🚨 Incident Reporting & Root Cause Tool")

    st.markdown("""
    Record incidents or near-misses, including basic details and a  
    simple **5 Whys analysis** to investigate the root cause.
    """)

    if "incident_log" not in st.session_state:
        st.session_state.incident_log = []

    with st.form("incident_form"):
        incident_type = st.selectbox("Type of Incident", ["Near Miss", "First Aid", "Medical Case", "Lost Time", "Fatality"])
        location = st.text_input("Location / Area")
        description = st.text_area("Incident Description")
        action_taken = st.text_area("Immediate Action Taken")
        date_occurred = st.date_input("Date", value=date.today())

        why1 = st.text_input("Why 1?")
        why2 = st.text_input("Why 2?")
        why3 = st.text_input("Why 3?")
        why4 = st.text_input("Why 4?")
        why5 = st.text_input("Why 5?")
        
        submitted = st.form_submit_button("➕ Submit Report")

    if submitted and description:
        st.session_state.incident_log.append({
            "Type": incident_type,
            "Location": location,
            "Description": description,
            "Date": str(date_occurred),
            "Action": action_taken,
            "Why 1": why1,
            "Why 2": why2,
            "Why 3": why3,
            "Why 4": why4,
            "Why 5": why5
        })

    if st.session_state.incident_log:
        st.subheader("📋 Incident Log")
        df = pd.DataFrame(st.session_state.incident_log)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export Incident Report", df.to_csv(index=False).encode("utf-8"), "incident_log.csv")
