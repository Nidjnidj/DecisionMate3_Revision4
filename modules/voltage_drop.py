import streamlit as st

def run(T):
    st.title("🔻 Voltage Drop Estimator")
    st.markdown("Estimate voltage drop over cable length based on load current and material.")

    current = st.number_input("Load Current (A)", min_value=0.0, value=10.0)
    length = st.number_input("One-way Cable Length (m)", min_value=0.0, value=50.0)
    voltage = st.number_input("System Voltage (V)", min_value=0.0, value=230.0)
    area = st.number_input("Conductor Cross-sectional Area (mm²)", min_value=0.1, value=2.5)
    material = st.selectbox("Conductor Material", ["Copper", "Aluminum"])

    resistivity = 0.0175 if material == "Copper" else 0.028  # Ohm·mm²/m

    if st.button("🔍 Estimate Voltage Drop"):
        try:
            vd = (2 * resistivity * length * current) / area  # V
            percent_drop = (vd / voltage) * 100
            st.success(f"Estimated Voltage Drop: {vd:.2f} V ({percent_drop:.2f}%)")
        except ZeroDivisionError:
            st.error("Cross-sectional area must be greater than zero.")

voltage_drop = run
