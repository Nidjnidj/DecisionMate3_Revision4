import streamlit as st
import pandas as pd
from datetime import date

def run(T):
    st.title("📝 HSE Audit & Inspection Planner")

    st.markdown("""
    Plan and log health, safety, and environmental audits/inspections.  
    Track findings, responsible persons, and close-out status.
    """)

    if "hse_audits" not in st.session_state:
        st.session_state.hse_audits = []

    with st.form("hse_audit_form"):
        audit_type = st.selectbox("Audit / Inspection Type", ["Internal", "External", "Regulatory", "Site Walkdown", "Toolbox"])
        area = st.text_input("Location / Area")
        finding = st.text_area("Key Finding")
        responsible = st.text_input("Responsible Person")
        status = st.selectbox("Status", ["Open", "In Progress", "Closed"])
        audit_date = st.date_input("Date", value=date.today())

        submitted = st.form_submit_button("➕ Add Audit")

    if submitted and area and finding:
        st.session_state.hse_audits.append({
            "Type": audit_type,
            "Area": area,
            "Finding": finding,
            "Responsible": responsible,
            "Status": status,
            "Date": str(audit_date)
        })

    if st.session_state.hse_audits:
        st.subheader("📋 HSE Audit Tracker")
        df = pd.DataFrame(st.session_state.hse_audits)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Log", df.to_csv(index=False).encode("utf-8"), "hse_audit_log.csv")
