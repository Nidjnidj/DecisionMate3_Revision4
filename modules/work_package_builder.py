import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("work_package_title", "Work Package Builder")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("work_package_builder", ""))

    if "wp_entries" not in st.session_state:
        st.session_state.wp_entries = []

    st.subheader(T.get("add_wp", "Define Work Package"))
    wp_name = st.text_input(T.get("wp_name", "Work Package Name"))
    scope = st.text_area(T.get("wp_scope", "Scope of Work"))
    start_date = st.date_input(T.get("wp_start", "Start Date"))
    end_date = st.date_input(T.get("wp_end", "End Date"))
    responsible = st.text_input(T.get("wp_responsible", "Responsible Party"))

    if st.button(T.get("add_wp_btn", "Add Work Package")) and wp_name:
        st.session_state.wp_entries.append({
            "Name": wp_name,
            "Scope": scope,
            "Start": str(start_date),
            "End": str(end_date),
            "Responsible": responsible
        })

    if st.session_state.wp_entries:
        df = pd.DataFrame(st.session_state.wp_entries)
        st.subheader(T.get("wp_table", "Work Packages"))
        st.dataframe(df)

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Name: {row['Name']}\n"
                f"Scope: {row['Scope']}\n"
                f"Start: {row['Start']} | End: {row['End']}\n"
                f"Responsible: {row['Responsible']}\n"
                "------------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="work_packages.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.wp_entries)
            st.success(T.get("save_success", "Work packages saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.wp_entries = data
                st.success(T.get("load_success", "Work packages loaded."))
            else:
                st.warning(T.get("load_warning", "No saved packages found."))

work_package_builder = run
