import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("discipline_ownership_title", "Discipline Ownership Map")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("discipline_ownership", ""))

    if "ownership_map" not in st.session_state:
        st.session_state.ownership_map = []

    st.subheader(T.get("add_entry", "Add Discipline Ownership"))
    discipline = st.text_input(T.get("discipline", "Discipline"))
    system = st.text_input(T.get("system_package", "System/Package"))
    responsible = st.text_input(T.get("responsible_party", "Responsible Party"))
    contact = st.text_input(T.get("contact", "Contact Person / Role"))
    notes = st.text_area(T.get("notes", "Notes"))

    if st.button(T.get("add_button", "Add Entry")) and discipline:
        st.session_state.ownership_map.append({
            "Discipline": discipline,
            "System/Package": system,
            "Responsible": responsible,
            "Contact": contact,
            "Notes": notes
        })

    if st.session_state.ownership_map:
        df = pd.DataFrame(st.session_state.ownership_map)
        st.subheader(T.get("ownership_table", "Ownership Map"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Discipline: {row['Discipline']}\n"
                f"System/Package: {row['System/Package']}\n"
                f"Responsible: {row['Responsible']}\n"
                f"Contact: {row['Contact']}\n"
                f"Notes: {row['Notes']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="discipline_ownership.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.ownership_map)
            st.success(T.get("save_success", "Ownership map saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.ownership_map = data
                st.success(T.get("load_success", "Ownership map loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

discipline_ownership = run
