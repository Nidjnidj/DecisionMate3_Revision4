import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("interface_risk_log_title", "Interface Risk Log")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("interface_risk_log", ""))

    if "interface_risks" not in st.session_state:
        st.session_state.interface_risks = []

    st.subheader(T.get("add_risk_entry", "Add Risk Entry"))
    interface_id = st.text_input(T.get("interface_id", "Interface ID"))
    risk_desc = st.text_area(T.get("risk_description", "Risk Description"))
    owner = st.text_input(T.get("owner", "Risk Owner"))
    mitigation = st.text_area(T.get("mitigation", "Mitigation Measures"))
    status = st.selectbox(T.get("status", "Status"), ["Open", "Mitigated", "Closed"])

    if st.button(T.get("add_button", "Add Entry")) and interface_id and risk_desc:
        st.session_state.interface_risks.append({
            "Interface ID": interface_id,
            "Risk Description": risk_desc,
            "Owner": owner,
            "Mitigation": mitigation,
            "Status": status
        })

    if st.session_state.interface_risks:
        df = pd.DataFrame(st.session_state.interface_risks)
        st.subheader(T.get("risk_table", "Interface Risk Log"))
        st.dataframe(df)

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Interface: {row['Interface ID']}\n"
                f"Risk: {row['Risk Description']}\n"
                f"Owner: {row['Owner']}\n"
                f"Mitigation: {row['Mitigation']}\n"
                f"Status: {row['Status']}\n"
                "---------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="interface_risk_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.interface_risks)
            st.success(T.get("save_success", "Risk log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.interface_risks = data
                st.success(T.get("load_success", "Risk log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

interface_risk_log = run