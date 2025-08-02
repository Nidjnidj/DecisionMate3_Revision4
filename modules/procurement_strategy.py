import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("procurement_strategy_title", "Procurement Strategy Canvas")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("procurement_strategy", ""))

    if "procurement_strategies" not in st.session_state:
        st.session_state.procurement_strategies = []

    st.subheader(T.get("add_procurement", "Add Procurement Package"))
    package = st.text_input(T.get("package_name", "Package Name"))
    description = st.text_area(T.get("description", "Description"))
    strategy = st.selectbox(T.get("strategy_type", "Strategy Type"), ["Competitive Bidding", "Single Source", "Framework Agreement", "Two-Stage Tender"])
    criticality = st.selectbox(T.get("criticality", "Criticality Level"), ["High", "Medium", "Low"])
    contract_type = st.selectbox(T.get("contract_type", "Contract Type"), ["Lump Sum", "Unit Rate", "Cost Plus", "Turnkey"])

    if st.button(T.get("add_button", "Add Strategy")) and package:
        st.session_state.procurement_strategies.append({
            "Package": package,
            "Description": description,
            "Strategy Type": strategy,
            "Criticality": criticality,
            "Contract Type": contract_type
        })

    if st.session_state.procurement_strategies:
        df = pd.DataFrame(st.session_state.procurement_strategies)
        st.subheader(T.get("strategy_table", "Procurement Strategies"))
        st.dataframe(df)

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Package: {row['Package']}\n"
                f"Strategy: {row['Strategy Type']} | Criticality: {row['Criticality']}\n"
                f"Contract Type: {row['Contract Type']}\n"
                f"Description: {row['Description']}\n"
                "-------------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="procurement_strategy.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.procurement_strategies)
            st.success(T.get("save_success", "Strategy saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.procurement_strategies = data
                st.success(T.get("load_success", "Strategy loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

procurement_strategy = run
