import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.title("📄 Instrument Specification Sheet")
    st.markdown(T.get("descriptions", {}).get("instrument_spec_sheet", ""))

    if "instrument_specs" not in st.session_state:
        st.session_state.instrument_specs = []

    st.subheader("➕ Add New Instrument")

    tag = st.text_input("Instrument Tag")
    type_ = st.selectbox("Instrument Type", ["Transmitter", "Switch", "Gauge", "Sensor", "Controller"])
    range_ = st.text_input("Measuring Range")
    unit = st.text_input("Unit")
    location = st.text_input("Installation Location")

    if st.button("Add Specification") and tag:
        st.session_state.instrument_specs.append({
            "Tag": tag,
            "Type": type_,
            "Range": range_,
            "Unit": unit,
            "Location": location
        })

    if st.session_state.instrument_specs:
        df = pd.DataFrame(st.session_state.instrument_specs)
        st.subheader("📋 Specification Table")
        st.dataframe(df)

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Instrument Specification Sheet", ln=True)
        for _, row in df.iterrows():
            line = f"Tag: {row['Tag']} | Type: {row['Type']} | Range: {row['Range']} {row['Unit']} | Location: {row['Location']}"
            pdf.multi_cell(0, 10, line)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button("Download PDF", pdf_output, file_name="instrument_spec_sheet.pdf", mime="application/pdf")

        if st.button("Save"):
            save_project(st.session_state.username, "Instrument Spec Sheet", st.session_state.instrument_specs)
            st.success("✅ Instrument data saved.")

        if st.button("Load"):
            data = load_project_data(st.session_state.username, "Instrument Spec Sheet")
            if data:
                st.session_state.instrument_specs = data
                st.success("✅ Data loaded.")
            else:
                st.warning("⚠️ No saved data found.")

instrument_spec_sheet = run
