import streamlit as st
import numpy as np

def run(T):
    st.header("🧪 Reservoir Property Calculator")

    st.markdown("### Porosity from Density Log")
    rho_ma = st.number_input("Matrix Density (g/cc)", value=2.65)
    rho_log = st.number_input("Density Log Reading (g/cc)", value=2.3)
    rho_f = st.number_input("Fluid Density (g/cc)", value=1.0)

    if rho_ma != rho_f:
        porosity = (rho_ma - rho_log) / (rho_ma - rho_f)
        st.success(f"Estimated Porosity: {porosity*100:.2f}%")
    else:
        st.warning("Matrix and fluid density cannot be equal.")

    st.markdown("---")
    st.markdown("### Water Saturation using Archie’s Equation")

    phi_archie = st.number_input("Porosity (fraction)", min_value=0.0, max_value=1.0, value=0.20)
    Rw = st.number_input("Formation Water Resistivity (Rw)", value=0.1)
    Rt = st.number_input("True Resistivity (Rt)", value=10.0)
    a = st.number_input("Tortuosity Factor (a)", value=1.0)
    m = st.number_input("Cementation Exponent (m)", value=2.0)
    n = st.number_input("Saturation Exponent (n)", value=2.0)

    if phi_archie > 0 and Rt > 0:
        F = a / (phi_archie ** m)
        Sw = ((F * Rw) / Rt) ** (1 / n)
        st.success(f"Estimated Water Saturation (Sw): {Sw*100:.2f}%")
        st.success(f"Estimated Hydrocarbon Saturation (1 - Sw): {(1 - Sw)*100:.2f}%")
    else:
        st.warning("Please enter valid porosity and resistivity values.")

    st.markdown("---")
    st.info("Permeability estimation module can be added in future updates.")
