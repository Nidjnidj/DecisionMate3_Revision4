import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("issue_escalation_title", "Issue Escalation Register")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("issue_escalation", ""))

    if "escalations" not in st.session_state:
        st.session_state.escalations = []

    st.subheader(T.get("add_escalation", "Add Escalation Entry"))
    issue_id = st.text_input(T.get("issue_id", "Issue ID"))
    date = st.date_input(T.get("escalation_date", "Escalation Date"))
    raised_by = st.text_input(T.get("raised_by", "Raised By"))
    description = st.text_area(T.get("issue_description", "Issue Description"))
    escalated_to = st.text_input(T.get("escalated_to", "Escalated To"))
    status = st.selectbox(T.get("status", "Status"), ["Open", "In Progress", "Resolved"])

    if st.button(T.get("add_button", "Add Escalation")) and issue_id:
        st.session_state.escalations.append({
            "Issue ID": issue_id,
            "Date": str(date),
            "Raised By": raised_by,
            "Description": description,
            "Escalated To": escalated_to,
            "Status": status
        })

    if st.session_state.escalations:
        df = pd.DataFrame(st.session_state.escalations)
        st.subheader(T.get("escalation_table", "Escalation Log"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Issue ID: {row['Issue ID']}\n"
                f"Date: {row['Date']}\n"
                f"Raised By: {row['Raised By']}\n"
                f"Description: {row['Description']}\n"
                f"Escalated To: {row['Escalated To']}\n"
                f"Status: {row['Status']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="issue_escalation_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.escalations)
            st.success(T.get("save_success", "Escalation log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.escalations = data
                st.success(T.get("load_success", "Escalation log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

issue_escalation = run
