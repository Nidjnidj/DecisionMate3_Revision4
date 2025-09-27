import streamlit as st
import pandas as pd
import numpy as np

def run():
    st.header("Market / Volume Scenarios")
    st.caption("Simple S-curve adoption feeding demand projections.")

    K = st.number_input("Saturation level (units/yr)", 100_000, 2_000_000, 300_000, step=10_000)
    r = st.slider("Growth steepness r", 0.1, 1.5, 0.5, 0.05)
    t0= st.slider("Inflection year t0", 0, 10, 3, 1)
    years = st.slider("Horizon (years)", 3, 15, 8)

    t = np.arange(years+1)
    demand = K/(1 + np.exp(-r*(t - t0)))
    df = pd.DataFrame({"Year": t, "Annual Demand": demand.astype(int)})
    st.line_chart(df.set_index("Year"))
    st.dataframe(df, use_container_width=True)
    st.download_button("Export CSV", df.to_csv(index=False).encode("utf-8"), "volume_scenarios.csv")
