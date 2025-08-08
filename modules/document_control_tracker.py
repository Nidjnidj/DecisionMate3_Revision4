import streamlit as st
import pandas as pd
from datetime import date

def run(T):
    st.title("📂 Document Control Tracker")

    st.markdown("""
    Use this tracker to manage engineering or quality documentation:  
    - Revision numbers  
    - Issue dates  
    - Approvers  
    - Current status  
    """)

    if "doc_log" not in st.session_state:
        st.session_state.doc_log = []

    with st.form("doc_form"):
        doc_title = st.text_input("Document Title")
        doc_number = st.text_input("Document Number / Code")
        revision = st.text_input("Revision Number")
        issue_date = st.date_input("Issue Date", value=date.today())
        status = st.selectbox("Status", ["Draft", "Issued for Review", "Issued for Approval", "Approved", "Superseded"])
        approver = st.text_input("Approver")

        submitted = st.form_submit_button("➕ Add Document Entry")

    if submitted and doc_number:
        st.session_state.doc_log.append({
            "Title": doc_title,
            "Number": doc_number,
            "Revision": revision,
            "Issue Date": str(issue_date),
            "Status": status,
            "Approver": approver
        })

    if st.session_state.doc_log:
        st.subheader("📋 Document Log")
        df = pd.DataFrame(st.session_state.doc_log)
        st.dataframe(df, use_container_width=True)

        st.download_button("📥 Export Document Log", df.to_csv(index=False).encode('utf-8'), "document_control_log.csv")
