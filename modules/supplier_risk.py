import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("supplier_risk_title", "Supplier Risk Log")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("supplier_risk", ""))

    if "supplier_risks" not in st.session_state:
        st.session_state.supplier_risks = []

    st.subheader(T.get("add_risk", "Add Supplier Risk"))
    supplier = st.text_input(T.get("supplier_name", "Supplier Name"))
    risk = st.text_area(T.get("risk_description", "Risk Description"))
    severity = st.selectbox(T.get("severity", "Severity Level"), ["Low", "Medium", "High"])
    mitigation = st.text_area(T.get("mitigation_plan", "Mitigation Plan"))

    if st.button(T.get("add_button", "Add Risk")) and supplier:
        st.session_state.supplier_risks.append({
            "Supplier": supplier,
            "Risk": risk,
            "Severity": severity,
            "Mitigation": mitigation
        })

    if st.session_state.supplier_risks:
        df = pd.DataFrame(st.session_state.supplier_risks)
        st.subheader(T.get("risk_log", "Supplier Risk Log"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Supplier: {row['Supplier']}\n"
                f"Risk: {row['Risk']}\n"
                f"Severity: {row['Severity']}\n"
                f"Mitigation: {row['Mitigation']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="supplier_risk_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.supplier_risks)
            st.success(T.get("save_success", "Risk log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.supplier_risks = data
                st.success(T.get("load_success", "Risk log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

supplier_risk = run
