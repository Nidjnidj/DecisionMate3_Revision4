import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("interface_matrix_title", "Interface Management Matrix")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("interface_matrix", ""))

    if "interfaces" not in st.session_state:
        st.session_state.interfaces = []

    st.subheader(T.get("add_interface", "Add Interface"))
    discipline1 = st.text_input(T.get("discipline_1", "Discipline A"))
    discipline2 = st.text_input(T.get("discipline_2", "Discipline B"))
    interface_desc = st.text_area(T.get("interface_description", "Interface Description"))
    status = st.selectbox(T.get("status", "Status"), ["Open", "Closed", "Pending Clarification"])

    if st.button(T.get("add_interface_btn", "Add Interface")) and discipline1 and discipline2:
        st.session_state.interfaces.append({
            "Discipline A": discipline1,
            "Discipline B": discipline2,
            "Description": interface_desc,
            "Status": status
        })

    if st.session_state.interfaces:
        df = pd.DataFrame(st.session_state.interfaces)
        st.subheader(T.get("interface_table", "Interface Matrix"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"{row['Discipline A']} → {row['Discipline B']}\n"
                f"Desc: {row['Description']}\n"
                f"Status: {row['Status']}\n"
                "----------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="interface_matrix.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.interfaces)
            st.success(T.get("save_success", "Interface data saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.interfaces = data
                st.success(T.get("load_success", "Interface data loaded."))
            else:
                st.warning(T.get("load_warning", "No interface data found."))

interface_matrix = run
