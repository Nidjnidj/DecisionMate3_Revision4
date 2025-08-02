import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("stakeholder_register_title", "Stakeholder Register")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("stakeholder_register", ""))

    if "stakeholder_register" not in st.session_state:
        st.session_state.stakeholder_register = []

    st.subheader(T.get("add_stakeholder", "Add Stakeholder"))
    name = st.text_input(T.get("stakeholder_name", "Name"))
    role = st.text_input(T.get("stakeholder_role", "Role"))
    influence = st.selectbox(T.get("influence_level", "Influence Level"), ["High", "Medium", "Low"])
    interest = st.selectbox(T.get("interest_level", "Interest Level"), ["High", "Medium", "Low"])
    strategy = st.text_area(T.get("engagement_strategy", "Engagement Strategy"))

    if st.button(T.get("add_button", "Add Stakeholder")) and name:
        st.session_state.stakeholder_register.append({
            "Name": name,
            "Role": role,
            "Influence": influence,
            "Interest": interest,
            "Strategy": strategy
        })

    if st.session_state.stakeholder_register:
        df = pd.DataFrame(st.session_state.stakeholder_register)
        st.subheader(T.get("stakeholder_table", "Stakeholder List"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Name: {row['Name']} | Role: {row['Role']}\n"
                f"Influence: {row['Influence']} | Interest: {row['Interest']}\n"
                f"Strategy: {row['Strategy']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="stakeholder_register.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.stakeholder_register)
            st.success(T.get("save_success", "Stakeholder register saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.stakeholder_register = data
                st.success(T.get("load_success", "Stakeholder register loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

stakeholder_register = run
