import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("valve_selector_title", "Valve Type Selector")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("valve_selector", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))

    fluid = st.selectbox(T.get("fluid_type", "Fluid Type"), ["Water", "Steam", "Gas", "Oil", "Chemicals"])
    flowrate = st.number_input(T.get("flowrate", "Flowrate (m3/h)"), min_value=0.1, value=100.0)
    pressure = st.number_input(T.get("pressure", "Operating Pressure (bar)"), min_value=0.1, value=10.0)
    temperature = st.number_input(T.get("temperature", "Temperature (°C)"), value=25.0)
    throttling = st.radio(T.get("throttling_required", "Is Flow Control Required?"), [T.get("yes", "Yes"), T.get("no", "No")])
    emergency = st.radio(T.get("emergency_protection", "Need for Emergency Shutoff/Safety?"), [T.get("yes", "Yes"), T.get("no", "No")])
    solids = st.checkbox(T.get("solid_particles", "Contains Solid Particles?"))

    st.subheader(T.get("results", "Results"))

    # Simple rule-based suggestion
    if emergency == T.get("yes", "Yes"):
        valve_type = "Safety Valve"
    elif throttling == T.get("yes", "Yes"):
        valve_type = "Control Valve"
    elif flowrate > 500:
        valve_type = "Butterfly Valve"
    elif pressure > 40:
        valve_type = "Globe Valve"
    elif solids:
        valve_type = "Gate Valve"
    else:
        valve_type = "Ball Valve"

    explanation = {
        "Safety Valve": "Used for emergency pressure relief to prevent equipment damage.",
        "Control Valve": "Used when precise flow regulation is required.",
        "Butterfly Valve": "Suitable for high flow, low pressure-drop systems.",
        "Globe Valve": "Recommended for high-pressure systems requiring throttling.",
        "Gate Valve": "Best for on/off services with solid-containing fluids.",
        "Ball Valve": "General-purpose valve for clean fluids and quick shutoff."
    }

    st.markdown(f"**{T.get('recommended_valve', 'Recommended Valve Type')}:** {valve_type}")
    st.info(explanation[valve_type])

    df = pd.DataFrame({
        "Parameter": ["Fluid Type", "Flowrate (m3/h)", "Pressure (bar)", "Temperature (°C)",
                      "Throttling Required", "Emergency Shutoff", "Solid Particles Present", "Suggested Valve"],
        "Value": [fluid, flowrate, pressure, temperature, throttling, emergency, solids, valve_type]
    })

    st.dataframe(df)

    # === Excel Export ===
    towrite = io.BytesIO()
    df.to_excel(towrite, index=False)
    towrite.seek(0)
    st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                       file_name="valve_selector.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # === PDF Export ===
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True)
    for i in range(len(df)):
        pdf.cell(200, 10, txt=f"{df.iloc[i, 0]}: {df.iloc[i, 1]}", ln=True)
    pdf.cell(200, 10, txt=f"Reason: {explanation[valve_type]}", ln=True)
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                       file_name="valve_selector.pdf", mime="application/pdf")

    # === Firebase Save/Load ===
    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, title, df.to_dict())
        st.success(T.get("save_success", "Project saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

valve_selector = run
