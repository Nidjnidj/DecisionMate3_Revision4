import streamlit as st

def run(T):
    st.title("🔌 Cable Sizing Calculator")

    st.markdown("""
    This tool helps you calculate appropriate cable size based on current, voltage, distance, and allowable voltage drop.
    """)

    current = st.number_input("Current (A)", min_value=0.0, format="%.2f")
    voltage = st.number_input("Voltage (V)", min_value=0.0, format="%.2f")
    length = st.number_input("Cable Length (m)", min_value=0.0, format="%.2f")
    allowable_drop = st.number_input("Allowable Voltage Drop (%)", min_value=0.0, max_value=10.0, format="%.2f")
    resistivity = st.selectbox("Conductor Material", ["Copper", "Aluminum"])

    if st.button("Calculate Size"):
        material_resistance = 0.0175 if resistivity == "Copper" else 0.0280  # Ohm.mm2/m
        voltage_drop_v = (voltage * allowable_drop) / 100
        try:
            area_mm2 = (2 * material_resistance * length * current) / voltage_drop_v
            st.success(f"Required minimum cross-sectional area: {area_mm2:.2f} mm²")
        except ZeroDivisionError:
            st.error("Voltage drop cannot be zero. Adjust input values.")

# ✅ Register function
cable_sizing = run
