import streamlit as st

def run(T):
    title = T.get("structural_load_title", "Structural Load Calculator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("structural_load_calculator", ""))

    st.subheader(T.get("load_input", "Input Parameters"))

    length = st.number_input(T.get("beam_length", "Beam Length (m)"), min_value=0.0, value=5.0)
    width = st.number_input(T.get("beam_width", "Beam Width (m)"), min_value=0.0, value=0.3)
    thickness = st.number_input(T.get("slab_thickness", "Slab Thickness (m)"), min_value=0.0, value=0.2)
    live_load = st.number_input(T.get("live_load", "Live Load (kN/m²)"), min_value=0.0, value=2.0)
    dead_load_factor = st.slider(T.get("dead_load_factor", "Dead Load Factor"), 1.0, 1.5, 1.2)
    density_concrete = st.number_input(T.get("density", "Concrete Density (kN/m³)"), min_value=0.0, value=24.0)

    if st.button(T.get("calculate_btn", "Calculate Total Load")):
        area = length * width
        dead_load = density_concrete * thickness
        total_load = area * (live_load + dead_load * dead_load_factor)

        st.success(T.get("total_load_result", "Total Load on Beam") + f": {total_load:.2f} kN")

structural_load_calculator = run
