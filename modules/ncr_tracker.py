import streamlit as st
import pandas as pd
from datetime import date

def run(T):
    st.title("📌 Non-Conformance Report (NCR) Tracker")

    st.markdown("""
    Log and track non-conformances across your project.  
    Include cause, corrective actions, and closure status.
    """)

    with st.form("ncr_form"):
        ncr_id = st.text_input("NCR ID / Reference")
        description = st.text_area("Description of Non-Conformance")
        responsible = st.text_input("Responsible Party")
        corrective_action = st.text_area("Corrective Action")
        status = st.selectbox("Status", ["Open", "In Progress", "Closed"])
        date_raised = st.date_input("Date Raised", value=date.today())

        submitted = st.form_submit_button("➕ Add NCR")

    if "ncr_log" not in st.session_state:
        st.session_state.ncr_log = []

    if submitted and ncr_id:
        st.session_state.ncr_log.append({
            "NCR ID": ncr_id,
            "Description": description,
            "Responsible": responsible,
            "Action": corrective_action,
            "Status": status,
            "Date": str(date_raised)
        })

    if st.session_state.ncr_log:
        st.subheader("🗃️ Logged NCRs")
        df = pd.DataFrame(st.session_state.ncr_log)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export NCR Log (CSV)", df.to_csv(index=False).encode('utf-8'), "ncr_log.csv")
