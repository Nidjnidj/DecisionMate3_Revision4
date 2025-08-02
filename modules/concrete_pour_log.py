import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("concrete_log_title", "Concrete Pour Log")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("concrete_pour_log", ""))

    if "pour_log" not in st.session_state:
        st.session_state.pour_log = []

    st.subheader(T.get("add_pour", "Log Pour Activity"))
    date = st.date_input(T.get("pour_date", "Pour Date"))
    location = st.text_input(T.get("pour_location", "Pour Location"))
    mix_type = st.text_input(T.get("mix_type", "Concrete Mix Type"))
    volume = st.number_input(T.get("pour_volume", "Volume (m³)"), min_value=0.0, value=0.0)

    if st.button(T.get("log_pour_btn", "Log Entry")) and location:
        st.session_state.pour_log.append({
            "Date": str(date),
            "Location": location,
            "Mix": mix_type,
            "Volume (m³)": volume
        })

    if st.session_state.pour_log:
        df = pd.DataFrame(st.session_state.pour_log)
        st.subheader(T.get("pour_log_table", "Logged Pours"))
        st.dataframe(df)
        st.success(T.get("total_volume", "Total Volume Logged") + f": {df['Volume (m³)'].sum():,.2f} m³")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Date']} | {row['Location']} | Mix: {row['Mix']} | Volume: {row['Volume (m³)']} m³"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="concrete_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.pour_log)
            st.success(T.get("save_success", "Concrete log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.pour_log = data
                st.success(T.get("load_success", "Concrete log loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

# ✅ Final export
concrete_pour_log = run
