def run(T):
    import streamlit as st
    import io
    from fpdf import FPDF
    from firebase_db import save_project, load_project_data

    st.header(T["heater_cooler_title"])
    st.markdown(T["descriptions"].get("heater_cooler_title", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))
    inlet_temp = st.number_input(T.get("inlet_temperature", "Inlet Temperature (°C)"), value=25.0)
    outlet_temp = st.number_input(T.get("outlet_temperature", "Outlet Temperature (°C)"), value=75.0)
    flowrate = st.number_input(T.get("flowrate", "Flowrate (m3/h)"), value=100.0)
    density = st.number_input(T.get("density", "Density (kg/m³)"), value=1000.0)
    cp = st.number_input(T.get("specific_heat", "Specific Heat (kJ/kg·°C)"), value=4.18)

    # Energy balance Q = m * Cp * deltaT
    mass_flow_kg_hr = flowrate * density
    delta_t = outlet_temp - inlet_temp
    energy_kj_hr = mass_flow_kg_hr * cp * delta_t
    energy_kw = energy_kj_hr / 3600

    st.subheader(T.get("results", "Results"))
    st.markdown(f"**{T.get('energy_required_kw', 'Energy Required')}:** {energy_kw:.2f} kW")

    if delta_t > 0:
        st.success(T.get("heating_result", "This is a heating operation."))
    elif delta_t < 0:
        st.info(T.get("cooling_result", "This is a cooling operation."))
    else:
        st.warning(T.get("no_temperature_change", "No temperature change detected."))

    if st.button(T["save"]):
        save_project(st.session_state.username, T["heater_cooler_title"], {
            "inlet_temp": inlet_temp,
            "outlet_temp": outlet_temp,
            "flowrate": flowrate,
            "density": density,
            "cp": cp,
            "energy_kw": energy_kw,
            "operation": "Heating" if delta_t > 0 else "Cooling" if delta_t < 0 else "None"
        })
        st.success(T["save_success"])

    if st.button(T["load"]):
        data = load_project_data(st.session_state.username, T["heater_cooler_title"])
        if data:
            st.json(data)
        else:
            st.warning(T["load_warning"])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=T["heater_cooler_title"], ln=True)
    pdf.multi_cell(0, 10, txt=f"Inlet Temp: {inlet_temp} °C\nOutlet Temp: {outlet_temp} °C\nFlowrate: {flowrate} m3/h\nDensity: {density} kg/m³\nCp: {cp} kJ/kg·°C\n\nEnergy Required: {energy_kw:.2f} kW")
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T["download_pdf"], data=pdf_output, file_name="heater_cooler_simulation.pdf", mime="application/pdf")
