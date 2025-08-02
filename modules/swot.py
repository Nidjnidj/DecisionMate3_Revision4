import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("swot_title", "SWOT Analyzer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("swot", ""))

    if "swot_entries" not in st.session_state:
        st.session_state.swot_entries = {"Strengths": [], "Weaknesses": [], "Opportunities": [], "Threats": []}

    categories = list(st.session_state.swot_entries.keys())
    selected_category = st.selectbox(T.get("select_category", "Select Category"), categories)
    entry = st.text_input(T.get("entry_text", "Enter item"))

    if st.button(T.get("add_item", "Add Item")) and entry:
        st.session_state.swot_entries[selected_category].append(entry)

    st.subheader(T.get("swot_matrix", "SWOT Matrix"))
    col1, col2 = st.columns(2)
    with col1:
        st.write("### " + T.get("strengths", "Strengths"))
        for s in st.session_state.swot_entries["Strengths"]:
            st.write("- ", s)

        st.write("### " + T.get("opportunities", "Opportunities"))
        for o in st.session_state.swot_entries["Opportunities"]:
            st.write("- ", o)

    with col2:
        st.write("### " + T.get("weaknesses", "Weaknesses"))
        for w in st.session_state.swot_entries["Weaknesses"]:
            st.write("- ", w)

        st.write("### " + T.get("threats", "Threats"))
        for t in st.session_state.swot_entries["Threats"]:
            st.write("- ", t)

    # PDF Export
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True)
    for cat, items in st.session_state.swot_entries.items():
        pdf.cell(200, 10, txt=cat, ln=True)
        for i in items:
            pdf.cell(200, 10, txt=f" - {i}", ln=True)

    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                       file_name="swot_matrix.pdf", mime="application/pdf")

    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, title, st.session_state.swot_entries)
        st.success(T.get("save_success", "SWOT saved."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            st.session_state.swot_entries = data
            st.success(T.get("load_success", "SWOT loaded."))
        else:
            st.warning(T.get("load_warning", "No saved SWOT data found."))

swot = run
