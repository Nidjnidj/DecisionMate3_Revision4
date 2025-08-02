import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("feedback_log_title", "Feedback & Expectation Log")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("feedback_log", ""))

    if "feedback_entries" not in st.session_state:
        st.session_state.feedback_entries = []

    st.subheader(T.get("add_entry", "Add Feedback/Expectation"))
    stakeholder = st.text_input(T.get("stakeholder_name", "Stakeholder Name"))
    feedback = st.text_area(T.get("feedback", "Feedback Provided"))
    expectation = st.text_area(T.get("expectation", "Expectation Stated"))
    response = st.text_area(T.get("response", "Your Response/Action"))

    if st.button(T.get("add_button", "Add Log")) and stakeholder:
        st.session_state.feedback_entries.append({
            "Stakeholder": stakeholder,
            "Feedback": feedback,
            "Expectation": expectation,
            "Response": response
        })

    if st.session_state.feedback_entries:
        df = pd.DataFrame(st.session_state.feedback_entries)
        st.subheader(T.get("feedback_table", "Feedback Log"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Stakeholder: {row['Stakeholder']}\n"
                f"Feedback: {row['Feedback']}\n"
                f"Expectation: {row['Expectation']}\n"
                f"Response: {row['Response']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="feedback_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.feedback_entries)
            st.success(T.get("save_success", "Feedback log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.feedback_entries = data
                st.success(T.get("load_success", "Feedback log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

feedback_log = run
