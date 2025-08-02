import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("stream_calc_title", "Stream Property Calculator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("stream_calculator", ""))

    st.subheader(T.get("stream_conditions", "Stream Conditions"))

    fluid_name = st.text_input(T.get("fluid_name", "Fluid Name"), value="Natural Gas")
    flowrate = st.number_input(T.get("flowrate_input", "Volumetric Flowrate (m³/h)"), min_value=0.0, value=1000.0)
    density = st.number_input(T.get("density_input", "Density (kg/m³)"), min_value=0.0, value=0.8)
    temperature = st.number_input(T.get("temperature", "Temperature (°C)"), value=25.0)
    pressure = st.number_input(T.get("pressure", "Pressure (bar)"), value=10.0)

    if st.button(T.get("calculate", "Calculate")):
        mass_flow_kg_hr = flowrate * density
        mass_flow_kg_s = mass_flow_kg_hr / 3600
        mass_flow_tph = mass_flow_kg_hr / 1000

        result = {
            "Fluid": fluid_name,
            "Volumetric Flowrate (m³/h)": round(flowrate, 2),
            "Density (kg/m³)": round(density, 2),
            "Mass Flowrate (kg/h)": round(mass_flow_kg_hr, 2),
            "Mass Flowrate (kg/s)": round(mass_flow_kg_s, 3),
            "Mass Flowrate (t/h)": round(mass_flow_tph, 3),
            "Temperature (°C)": temperature,
            "Pressure (bar)": pressure
        }

        df = pd.DataFrame(list(result.items()), columns=["Property", "Value"])
        st.subheader(T.get("calculated_properties", "Calculated Properties"))
        st.dataframe(df)

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="stream_properties.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            pdf.cell(200, 10, txt=f"{df.iloc[i, 0]}: {df.iloc[i, 1]}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="stream_properties.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, result)
            st.success(T.get("save_success", "Project saved successfully."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.json(data)
            else:
                st.warning(T.get("load_warning", "No saved data found."))

stream_calculator = run
