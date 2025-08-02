import streamlit as st
import pandas as pd
import math
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("pipe_sizing_title", "Pipe & Line Sizing Tool")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("pipe_sizing", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))

    fluid = st.selectbox(T.get("fluid_type", "Fluid Type"), ["Water", "Oil", "Gas"])
    flowrate = st.number_input(T.get("flowrate", "Flowrate (m3/h)"), min_value=0.1, value=100.0)
    velocity = st.number_input(T.get("velocity", "Desired Velocity (m/s)"), min_value=0.1, value=1.5)
    length = st.number_input(T.get("length", "Pipe Length (m)"), min_value=1.0, value=100.0)
    roughness = st.number_input(T.get("roughness", "Pipe Roughness (mm)"), min_value=0.001, value=0.05)
    density = st.number_input(T.get("density", "Fluid Density (kg/m3)"), min_value=1.0, value=1000.0)
    viscosity = st.number_input(T.get("viscosity", "Fluid Viscosity (cP)"), min_value=0.01, value=1.0)

    st.subheader(T.get("results", "Results"))

    area = (flowrate / 3600) / velocity  # m2
    diameter = math.sqrt((4 * area) / math.pi)  # m

    reynolds = (density * velocity * diameter) / (viscosity / 1000)  # Re = ρvd/μ

    # Darcy friction factor using Haaland's equation
    relative_roughness = roughness / 1000 / diameter
    f = 0.0
    if reynolds != 0:
        f = (-1.8 * math.log10((6.9 / reynolds) + (relative_roughness / 3.7)**1.11))**-2

    pressure_drop = f * (length / diameter) * (density * velocity**2 / 2) / 100000  # bar

    st.markdown(f"**{T.get('pipe_diameter', 'Required Pipe Diameter')}:** {diameter:.3f} m")
    st.markdown(f"**{T.get('reynolds_number', 'Reynolds Number')}:** {reynolds:,.0f}")
    st.markdown(f"**{T.get('pressure_drop', 'Estimated Pressure Drop')}:** {pressure_drop:.3f} bar")

    # Prepare dataframe
    result_df = pd.DataFrame({
        "Parameter": ["Fluid", "Flowrate (m3/h)", "Velocity (m/s)", "Length (m)", "Roughness (mm)",
                      "Density (kg/m3)", "Viscosity (cP)", "Diameter (m)", "Reynolds", "Pressure Drop (bar)"],
        "Value": [fluid, flowrate, velocity, length, roughness, density, viscosity, f"{diameter:.3f}",
                  f"{reynolds:,.0f}", f"{pressure_drop:.3f}"]
    })

    st.dataframe(result_df)

    # === Export Excel ===
    towrite = io.BytesIO()
    result_df.to_excel(towrite, index=False)
    towrite.seek(0)
    st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                       file_name="pipe_line_sizing.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # === Export PDF ===
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True)
    for i in range(len(result_df)):
        pdf.cell(200, 10, txt=f"{result_df.iloc[i, 0]}: {result_df.iloc[i, 1]}", ln=True)
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                       file_name="pipe_line_sizing.pdf", mime="application/pdf")

    # === Firebase Save/Load ===
    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, title, result_df.to_dict())
        st.success(T.get("save_success", "Project saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

pipe_line_sizing = run
