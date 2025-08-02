import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("sensor_calibration_title", "Sensor Calibration Tracker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("sensor_calibration", ""))

    if "sensor_calibration_log" not in st.session_state:
        st.session_state.sensor_calibration_log = []

    st.subheader(T.get("add_entry", "Add Calibration Entry"))
    tag = st.text_input(T.get("tag", "Sensor Tag"))
    last_cal = st.date_input(T.get("last_calibrated", "Last Calibrated"))
    next_due = st.date_input(T.get("next_due", "Next Due"))
    technician = st.text_input(T.get("technician", "Technician"))
    status = st.selectbox(T.get("status", "Status"), ["Calibrated", "Pending", "Overdue"])

    if st.button(T.get("add_button", "Add Entry")) and tag and technician:
        st.session_state.sensor_calibration_log.append({
            "Sensor Tag": tag,
            "Last Calibrated": str(last_cal),
            "Next Due": str(next_due),
            "Technician": technician,
            "Status": status
        })

    if st.session_state.sensor_calibration_log:
        df = pd.DataFrame(st.session_state.sensor_calibration_log)
        st.subheader(T.get("calibration_table", "Calibration Log"))
        st.dataframe(df)

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Tag: {row['Sensor Tag']}\n"
                f"Last: {row['Last Calibrated']} | Next: {row['Next Due']}\n"
                f"Technician: {row['Technician']} | Status: {row['Status']}\n"
                "---------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="sensor_calibration_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.sensor_calibration_log)
            st.success(T.get("save_success", "Calibration log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.sensor_calibration_log = data
                st.success(T.get("load_success", "Calibration log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

sensor_calibration = run
