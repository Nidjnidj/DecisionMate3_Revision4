import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

def run(T):
    st.header("📉 Decline Curve Analyzer")

    st.markdown("### Input Parameters")

    q_i = st.number_input("Initial Production Rate (bbl/day)", min_value=0.0, value=1000.0)
    D = st.number_input("Decline Rate (per year)", min_value=0.0, value=0.2, step=0.01, format="%.4f")
    b = st.number_input("Hyperbolic Exponent (b)", min_value=0.0, value=0.5, step=0.1)
    t_max = st.slider("Forecast Duration (years)", 1, 30, 10)
    decline_type = st.selectbox("Decline Type", ["Exponential", "Harmonic", "Hyperbolic"])

    t = np.linspace(0, t_max, 100)

    if decline_type == "Exponential":
        q = q_i * np.exp(-D * t)
    elif decline_type == "Harmonic":
        q = q_i / (1 + D * t)
    elif decline_type == "Hyperbolic":
        q = q_i * (1 + b * D * t) ** (-1 / b)

    cumulative = np.trapz(q, t) * 365  # barrels

    st.markdown(f"**Estimated Cumulative Production:** {cumulative:,.2f} barrels")

    fig, ax = plt.subplots()
    ax.plot(t, q, label="Rate (q)", color="blue")
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Production Rate (bbl/day)")
    ax.set_title(f"{decline_type} Decline Curve")
    ax.grid(True)
    st.pyplot(fig)
