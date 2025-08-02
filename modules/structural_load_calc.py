import streamlit as st

def structural_load_calc(T):
    st.header("🏗️ " + T.get("structural_load_calc_title", "Structural Load Calculator"))

    st.markdown("### Input Structural Parameters")

    span = st.number_input("Beam Span (m)", min_value=0.0, value=6.0)
    load_per_m = st.number_input("Load per meter (kN/m)", min_value=0.0, value=10.0)
    safety_factor = st.slider("Safety Factor", 1.0, 2.5, 1.5)

    if st.button("Calculate Total Load"):
        total_load = load_per_m * span * safety_factor
        st.success(f"✅ Total Factored Load: {total_load:.2f} kN")

    st.markdown("---")
    st.caption("This simple tool calculates the total structural load for beam design using basic inputs.")

# ✅ Required for app.py registration
structural_load_calculator = structural_load_calc
