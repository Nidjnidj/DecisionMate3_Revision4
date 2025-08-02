import streamlit as st
import math
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T.get("valve_drop_title", "Valve Pressure Drop Estimator"))
    st.markdown(T.get("descriptions", {}).get("valve_drop_title", "Estimate pressure drop across valves using Cv."))

    st.subheader(T.get("input_parameters", "Input Parameters"))

    cv = st.number_input(T.get("cv_value", "Valve Flow Coefficient (Cv)"), min_value=0.01, value=10.0, step=0.1)
    flowrate = st.number_input(T.get("flowrate", "Flowrate (m³/h)"), min_value=0.01, value=100.0, step=1.0)
    density = st.number_input(T.get("density", "Fluid Density (kg/m³)"), min_value=0.01, value=1000.0, step=1.0)

    st.subheader(T.get("results", "Results"))

    try:
        q_gpm = flowrate * 4.40287  # m³/h to US gpm
        sg = density / 1000  # Specific gravity
        delta_p = ((q_gpm / cv) ** 2) * sg * 0.433  # Pressure drop in bar
        st.success(f"{T.get('pressure_drop', 'Estimated Pressure Drop')}: {delta_p:.3f} bar")
    except Exception as e:
        st.error(f"Calculation error: {e}")

    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, T.get("valve_drop_title", "Valve Pressure Drop Estimator"), {
            "cv": cv,
            "flowrate": flowrate,
            "density": density,
            "pressure_drop": delta_p
        })
        st.success(T.get("save_success", "Project saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, T.get("valve_drop_title", "Valve Pressure Drop Estimator"))
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=T.get("valve_drop_title", "Valve Pressure Drop Estimator"), ln=True)
    pdf.multi_cell(0, 10, txt=f"Cv: {cv}\nFlowrate: {flowrate} m³/h\nDensity: {density} kg/m³\n\nPressure Drop: {delta_p:.3f} bar")
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))

    st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output, file_name="valve_drop_result.pdf", mime="application/pdf")

valve_drop = run
