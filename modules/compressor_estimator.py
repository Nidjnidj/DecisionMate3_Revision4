import streamlit as st
import pandas as pd
import math
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("compressor_estimator_title", "Compressor Power Estimator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("compressor_estimator", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))

    compressor_type = st.selectbox(T.get("compressor_type", "Compressor Type"),
                                   ["Centrifugal", "Reciprocating", "Screw"])
    flowrate = st.number_input(T.get("flowrate", "Flowrate (m3/h)"), min_value=0.1, value=1000.0)
    suction_pressure = st.number_input(T.get("suction_pressure", "Suction Pressure (bar abs)"), min_value=0.1, value=1.0)
    discharge_pressure = st.number_input(T.get("discharge_pressure", "Discharge Pressure (bar abs)"), min_value=suction_pressure + 0.1, value=5.0)
    temperature = st.number_input(T.get("temperature", "Temperature (°C)"), value=25.0)
    k = st.number_input(T.get("k_value", "Isentropic Exponent (k)"), min_value=1.0, max_value=2.0, value=1.3)
    z = st.number_input(T.get("z_factor", "Compressibility Factor (Z)"), min_value=0.1, max_value=1.2, value=1.0)

    st.subheader(T.get("results", "Results"))

    R = 8.314  # J/mol·K
    MW = st.number_input(T.get("molecular_weight", "Molecular Weight (g/mol)"), min_value=1.0, value=18.0)  # example: air ~29, methane ~16

    T_abs = temperature + 273.15  # K
    P1 = suction_pressure * 1e5  # Pa
    P2 = discharge_pressure * 1e5  # Pa

    # Convert flowrate to m3/s
    q = flowrate / 3600

    # Gas density at inlet
    rho = (P1 * MW / 1000) / (z * R * T_abs)  # kg/m3

    # Isentropic compression power formula
    n = (k / (k - 1)) * P1 * q * (((P2 / P1) ** ((k - 1) / k)) - 1)  # J/s = W
    power_kW = n / 1000  # in kW

    st.markdown(f"**{T.get('estimated_power', 'Estimated Power Required')}:** {power_kW:.2f} kW")
    st.markdown(f"**{T.get('gas_density', 'Inlet Gas Density')}:** {rho:.2f} kg/m³")

    df = pd.DataFrame({
        "Parameter": ["Compressor Type", "Flowrate (m3/h)", "Suction Pressure (bar)", "Discharge Pressure (bar)",
                      "Temperature (°C)", "Isentropic Exponent (k)", "Compressibility (Z)", "Molecular Weight (g/mol)",
                      "Inlet Gas Density (kg/m3)", "Estimated Power (kW)"],
        "Value": [compressor_type, flowrate, suction_pressure, discharge_pressure,
                  temperature, k, z, MW, f"{rho:.2f}", f"{power_kW:.2f}"]
    })

    st.dataframe(df)

    # Excel export
    towrite = io.BytesIO()
    df.to_excel(towrite, index=False)
    towrite.seek(0)
    st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                       file_name="compressor_power.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # PDF export
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True)
    for i in range(len(df)):
        pdf.cell(200, 10, txt=f"{df.iloc[i, 0]}: {df.iloc[i, 1]}", ln=True)
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                       file_name="compressor_power.pdf", mime="application/pdf")

    # Firebase save/load
    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, title, df.to_dict())
        st.success(T.get("save_success", "Project saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

compressor_estimator = run
