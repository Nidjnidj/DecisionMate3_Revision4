import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("communication_tracker_title", "Communication Tracker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("communication_tracker", ""))

    if "communications" not in st.session_state:
        st.session_state.communications = []

    st.subheader(T.get("add_comm", "Add Communication"))
    stakeholder = st.text_input(T.get("stakeholder_name", "Stakeholder Name"))
    date = st.date_input(T.get("comm_date", "Date of Communication"))
    method = st.text_input(T.get("communication_method", "Method Used"))
    summary = st.text_area(T.get("summary", "Communication Summary"))

    if st.button(T.get("add_button", "Add Record")) and stakeholder:
        st.session_state.communications.append({
            "Stakeholder": stakeholder,
            "Date": str(date),
            "Method": method,
            "Summary": summary
        })

    if st.session_state.communications:
        df = pd.DataFrame(st.session_state.communications)
        st.subheader(T.get("comm_table", "Communication Records"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Stakeholder: {row['Stakeholder']}\n"
                f"Date: {row['Date']}\n"
                f"Method: {row['Method']}\n"
                f"Summary: {row['Summary']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="communication_tracker.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.communications)
            st.success(T.get("save_success", "Communication log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.communications = data
                st.success(T.get("load_success", "Communication log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

communication_tracker = run
