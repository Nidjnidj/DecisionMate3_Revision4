import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("interdependency_tracker_title", "Interdependency Tracker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("interdependency_tracker", ""))

    if "interdependencies" not in st.session_state:
        st.session_state.interdependencies = []

    st.subheader(T.get("add_dependency", "Add Dependency"))
    source = st.text_input(T.get("source_discipline", "Source Discipline"))
    target = st.text_input(T.get("target_discipline", "Target Discipline"))
    description = st.text_area(T.get("dependency_description", "Dependency Description"))
    status = st.selectbox(T.get("status", "Status"), ["Open", "In Progress", "Resolved"])
    notes = st.text_area(T.get("notes", "Notes"))

    if st.button(T.get("add_button", "Add Dependency")) and source and target:
        st.session_state.interdependencies.append({
            "Source": source,
            "Target": target,
            "Description": description,
            "Status": status,
            "Notes": notes
        })

    if st.session_state.interdependencies:
        df = pd.DataFrame(st.session_state.interdependencies)
        st.subheader(T.get("dependency_table", "Interdependency List"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Source: {row['Source']} → Target: {row['Target']}\n"
                f"Description: {row['Description']}\n"
                f"Status: {row['Status']}\n"
                f"Notes: {row['Notes']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="interdependencies.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.interdependencies)
            st.success(T.get("save_success", "Dependencies saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.interdependencies = data
                st.success(T.get("load_success", "Dependencies loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

interdependency_tracker = run
