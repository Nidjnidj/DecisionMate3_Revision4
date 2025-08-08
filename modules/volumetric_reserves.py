import streamlit as st

def run(T):
    st.header("🛢️ Volumetric Reserves Estimator")

    st.markdown("### Input Reservoir Parameters")

    area = st.number_input("Reservoir Area (acres)", min_value=0.0, step=100.0)
    net_pay = st.number_input("Net Pay Thickness (ft)", min_value=0.0, step=1.0)
    porosity = st.number_input("Porosity (%)", min_value=0.0, max_value=100.0, step=0.1)
    saturation = st.number_input("Hydrocarbon Saturation (%)", min_value=0.0, max_value=100.0, step=0.1)
    fv_factor = st.number_input("Formation Volume Factor (bbl/STB for oil or res ft³/SCF for gas)", min_value=0.0001, step=0.01)

    fluid_type = st.selectbox("Fluid Type", ["Oil", "Gas"])

    if st.button("Calculate Reserves"):
        if fluid_type == "Oil":
            stoiip = (7758 * area * net_pay * (porosity / 100) * (saturation / 100)) / fv_factor
            st.success(f"Estimated STOIIP: {stoiip:,.2f} barrels")
        elif fluid_type == "Gas":
            ogip = (43560 * area * net_pay * (porosity / 100) * (saturation / 100)) / fv_factor
            st.success(f"Estimated OGIP: {ogip:,.2f} standard cubic feet (scf)")
