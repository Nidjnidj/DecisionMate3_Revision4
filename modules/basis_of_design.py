import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("basis_title", "Basis of Design Developer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("basis_of_design", ""))

    st.subheader(T.get("project_info", "Project Information"))
    project_name = st.text_input(T.get("project_name", "Project Name"))
    discipline = st.selectbox(T.get("discipline", "Discipline"),
                              ["Process", "Mechanical", "Piping", "Civil", "Electrical", "Instrumentation", "HSE"])

    st.subheader(T.get("design_parameters", "Design Parameters"))
    param_name = st.text_input(T.get("param_name", "Parameter Name"), key="param")
    param_value = st.text_input(T.get("param_value", "Value"), key="value")
    param_unit = st.text_input(T.get("param_unit", "Unit"), key="unit")
    param_source = st.text_input(T.get("param_source", "Source/Justification"), key="source")

    if "bod_table" not in st.session_state:
        st.session_state.bod_table = []

    if st.button(T.get("add_param", "Add Parameter")):
        st.session_state.bod_table.append({
            "Parameter": param_name,
            "Value": param_value,
            "Unit": param_unit,
            "Source": param_source
        })

    df = pd.DataFrame(st.session_state.bod_table)

    if not df.empty:
        st.subheader(T.get("basis_table", "Basis of Design Table"))
        st.dataframe(df)

        # === Excel Export ===
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name="BasisOfDesign", index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="basis_of_design.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"{title} - {project_name}", ln=True)
        pdf.cell(200, 10, txt=f"Discipline: {discipline}", ln=True)
        for i in range(len(df)):
            row = df.iloc[i]
            pdf.cell(200, 10, txt=f"{row['Parameter']}: {row['Value']} {row['Unit']} ({row['Source']})", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="basis_of_design.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, f"{title} - {project_name}", df.to_dict())
            st.success(T.get("save_success", "Project saved successfully."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, f"{title} - {project_name}")
            if data:
                df_loaded = pd.DataFrame(data)
                st.session_state.bod_table = df_loaded.to_dict(orient='records')
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

basis_of_design = run
