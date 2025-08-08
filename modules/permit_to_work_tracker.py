import streamlit as st
import pandas as pd
from datetime import date

def run(T):
    st.title("📄 Permit to Work Tracker")

    st.markdown("""
    Manage and monitor the status of work permits issued on your site.
    Track permit type, area, validity dates, and status.
    """)

    if "permits_log" not in st.session_state:
        st.session_state.permits_log = []

    with st.form("permit_form"):
        permit_id = st.text_input("Permit ID / Reference")
        permit_type = st.selectbox("Permit Type", [
            "Hot Work", "Confined Space", "Electrical", "Working at Height", "Excavation", "General"
        ])
        area = st.text_input("Work Area / Location")
        issued_date = st.date_input("Issued Date", value=date.today())
        expiry_date = st.date_input("Expiry Date")
        status = st.selectbox("Permit Status", ["Open", "Closed", "Suspended"])

        submitted = st.form_submit_button("➕ Add Permit")

    if submitted and permit_id:
        st.session_state.permits_log.append({
            "Permit ID": permit_id,
            "Type": permit_type,
            "Area": area,
            "Issued Date": str(issued_date),
            "Expiry Date": str(expiry_date),
            "Status": status
        })

    if st.session_state.permits_log:
        st.subheader("📋 Active Permit Register")
        df = pd.DataFrame(st.session_state.permits_log)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export Permit Log", df.to_csv(index=False).encode("utf-8"), "permit_register.csv")
