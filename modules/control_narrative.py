import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("control_narrative_title", "Control Narrative Builder")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("control_narrative", ""))

    if "control_narratives" not in st.session_state:
        st.session_state.control_narratives = []

    st.subheader(T.get("add_narrative", "Add Control Narrative"))
    system = st.text_input(T.get("system_name", "System Name"))
    operation_mode = st.selectbox(T.get("operation_mode", "Operation Mode"), ["Manual", "Auto", "Remote", "Other"])
    sequence = st.text_area(T.get("sequence", "Control Sequence"))
    alarms = st.text_area(T.get("alarms", "Alarms & Interlocks"))
    notes = st.text_area(T.get("notes", "Additional Notes"))

    if st.button(T.get("add_button", "Add Narrative")) and system:
        st.session_state.control_narratives.append({
            "System": system,
            "Mode": operation_mode,
            "Sequence": sequence,
            "Alarms": alarms,
            "Notes": notes
        })

    if st.session_state.control_narratives:
        df = pd.DataFrame(st.session_state.control_narratives)
        st.subheader(T.get("narrative_table", "Control Narratives"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"System: {row['System']} | Mode: {row['Mode']}\n"
                f"Sequence: {row['Sequence']}\n"
                f"Alarms: {row['Alarms']}\n"
                f"Notes: {row['Notes']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="control_narratives.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.control_narratives)
            st.success(T.get("save_success", "Narrative saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.control_narratives = data
                st.success(T.get("load_success", "Narrative loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

control_narrative = run
