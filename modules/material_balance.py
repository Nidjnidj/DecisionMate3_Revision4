import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def run(T):
    st.header("⚖️ Material Balance Calculator (Tank Model)")

    st.markdown("### Input Reservoir Data")

    st.info("This tool assumes a simplified, undersaturated oil reservoir with no water influx.")

    p_i = st.number_input("Initial Pressure (psia)", min_value=0.0, value=3500.0)
    b_o_i = st.number_input("Initial Oil FVF (bbl/STB)", min_value=0.0, value=1.2)
    c_t = st.number_input("Total Compressibility (1/psi)", min_value=0.0, value=1e-5, format="%.6f")
    
    st.markdown("### Input Production and Pressure History")

    uploaded_file = st.file_uploader("Upload CSV File with 'P' (pressure, psia) and 'F' (fluid withdrawal, STB)", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "P" in df.columns and "F" in df.columns:
            df["E_t"] = (b_o_i * c_t * (p_i - df["P"]))  # simplified Et formula
            df["N"] = df["F"] / df["E_t"]
            N_est = df["N"].mean()

            st.markdown(f"**Estimated Original Oil In Place (OOIP):** {N_est:,.2f} STB")
            st.line_chart(df[["F", "E_t"]])

            st.subheader("Raw Calculated Table")
            st.dataframe(df.round(4))

        else:
            st.error("CSV must contain columns: 'P' and 'F'")
    else:
        st.warning("Please upload CSV to continue.")
