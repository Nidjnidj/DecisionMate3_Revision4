import streamlit as st
import math
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T.get("flash_calc_title", "Flash Calculation"))
    st.markdown(T.get("descriptions", {}).get("flash_calc_title", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))
    pressure = st.number_input(T.get("pressure", "System Pressure (bar)"), min_value=0.01, value=1.0)
    temperature = st.number_input(T.get("temperature", "System Temperature (°C)"), value=100.0)
    component = st.selectbox(T.get("component", "Component"), ["Water", "Methanol", "Ethanol", "Benzene"])

    antoine_constants = {
        "Water": (8.07131, 1730.63, 233.426),
        "Methanol": (8.0724, 1574.99, 238.78),
        "Ethanol": (8.20417, 1642.89, 230.3),
        "Benzene": (6.90565, 1211.033, 220.79)
    }

    A, B, C = antoine_constants[component]
    Psat_mmHg = 10 ** (A - (B / (temperature + C)))
    Psat_bar = Psat_mmHg * 0.00133322
    K_value = Psat_bar / pressure

    st.subheader(T.get("results", "Results"))
    st.markdown(f"**{T.get('component', 'Component')}:** {component}")
    st.markdown(f"**{T.get('vapor_pressure', 'Vapor Pressure')}:** {Psat_bar:.3f} bar")
    st.markdown(f"**{T.get('k_value', 'Equilibrium K-value')}:** {K_value:.3f}")

    if K_value > 1:
        phase = T.get("partial_vapor", "Partially Vaporized")
    elif K_value < 1:
        phase = T.get("partial_liquid", "Partially Condensed")
    else:
        phase = T.get("equilibrium", "At Equilibrium")

    st.success(f"{T.get('phase_state', 'Predicted Phase State')}: {phase}")

    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, T.get("flash_calc_title", "Flash Calculation"), {
            "component": component,
            "pressure": pressure,
            "temperature": temperature,
            "psat_bar": Psat_bar,
            "k_value": K_value,
            "phase_prediction": phase
        })
        st.success(T.get("save_success", "Project saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, T.get("flash_calc_title", "Flash Calculation"))
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=T.get("flash_calc_title", "Flash Calculation"), ln=True)
    pdf.multi_cell(0, 10, txt=f"Component: {component}\nPressure: {pressure} bar\nTemperature: {temperature} °C\n\nVapor Pressure: {Psat_bar:.3f} bar\nK-value: {K_value:.3f}\nPhase: {phase}")
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output, file_name="flash_calc_result.pdf", mime="application/pdf")

flash_calc = run
