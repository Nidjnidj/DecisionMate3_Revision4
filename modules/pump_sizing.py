import streamlit as st
import math
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T.get("pump_sizing_title", "Pump Selector & Sizing"))
    st.markdown(T.get("descriptions", {}).get("pump_sizing_title", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))
    flowrate = st.number_input(T.get("flowrate", "Flowrate (m³/h)"), min_value=0.0, value=50.0)
    head = st.number_input(T.get("head", "Total Head (m)"), min_value=0.0, value=30.0)
    sg = st.number_input(T.get("specific_gravity", "Specific Gravity"), min_value=0.0, value=1.0)
    efficiency = st.slider(T.get("efficiency", "Pump Efficiency (%)"), 10, 100, 70)

    st.subheader(T.get("npsh_section", "NPSH"))
    npsh_available = st.number_input(T.get("npsh_available", "NPSH Available (m)"), min_value=0.0, value=6.0)
    npsh_required = st.number_input(T.get("npsh_required", "NPSH Required (m)"), min_value=0.0, value=4.0)

    power_kw = (flowrate * head * sg * 9.81) / (3600 * (efficiency / 100))
    npsh_margin = npsh_available - npsh_required

    st.subheader(T.get("results", "Results"))
    st.markdown(f"**{T.get('power_required', 'Power Required')}:** {power_kw:.2f} kW")
    st.markdown(f"**{T.get('npsh_margin', 'NPSH Margin')}:** {npsh_margin:.2f} m")

    if npsh_margin < 1:
        st.warning(T.get("npsh_warning", "NPSH margin is low – risk of cavitation."))
    else:
        st.success(T.get("npsh_ok", "NPSH margin is sufficient."))

    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, T.get("pump_sizing_title", "Pump Selector & Sizing"), {
            "flowrate": flowrate,
            "head": head,
            "specific_gravity": sg,
            "efficiency": efficiency,
            "npsh_available": npsh_available,
            "npsh_required": npsh_required,
            "power_kw": power_kw,
            "npsh_margin": npsh_margin
        })
        st.success(T.get("save_success", "Project saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, T.get("pump_sizing_title", "Pump Selector & Sizing"))
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

    # PDF Export
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=T.get("pump_sizing_title", "Pump Selector & Sizing"), ln=True)
    pdf.multi_cell(0, 10, txt=(
        f"Flowrate: {flowrate} m³/h\n"
        f"Head: {head} m\n"
        f"Specific Gravity: {sg}\n"
        f"Efficiency: {efficiency} %\n\n"
        f"NPSH Available: {npsh_available} m\n"
        f"NPSH Required: {npsh_required} m\n"
        f"NPSH Margin: {npsh_margin:.2f} m\n\n"
        f"Power Required: {power_kw:.2f} kW"
    ))
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(
        label=T.get("download_pdf", "Download PDF"),
        data=pdf_output,
        file_name="pump_sizing_result.pdf",
        mime="application/pdf"
    )

pump_selector = run
