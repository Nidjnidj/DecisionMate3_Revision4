import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io

def run(T):
    st.title("📉 MBAL (Material Balance) Model")
    st.markdown("Analyze reservoir pressure behavior using material balance equations.")

    st.subheader("🔧 Reservoir & Production Inputs")
    P_i = st.number_input("Initial Pressure Pᵢ (psi)", value=3000.0)
    B_o = st.number_input("Oil Formation Volume Factor Bᵒ (rb/stb)", value=1.2)
    N = st.number_input("Original Oil In Place (OOIP), N (stb)", value=1e6)

    st.markdown("### 📊 Production History")
    num_points = st.number_input("Number of Production Points", min_value=2, value=5)

    production_data = []
    for i in range(int(num_points)):
        col1, col2 = st.columns(2)
        with col1:
            p = st.number_input(f"Reservoir Pressure P[{i+1}] (psi)", key=f"p_{i}", value=P_i - i * 100)
        with col2:
            Np = st.number_input(f"Cumulative Oil Production Np[{i+1}] (stb)", key=f"Np_{i}", value=(i + 1) * 10000)
        production_data.append((p, Np))

    df = pd.DataFrame(production_data, columns=["P", "Np"])
    df["F"] = df["Np"] * B_o
    df["Eo"] = (P_i - df["P"]) / P_i  # simplified expansion term

    st.subheader("📈 MBAL Diagnostic Plot")
    fig, ax = plt.subplots()
    ax.plot(df["Eo"], df["F"], "o-", label="F vs. Eo")
    ax.set_xlabel("Eo (Dimensionless Expansion)")
    ax.set_ylabel("F (Cumulative Withdrawal)")
    ax.set_title("MBAL Diagnostic Plot")
    ax.grid(True)
    st.pyplot(fig)

    st.subheader("📃 Interpretation")
    slope, intercept = np.polyfit(df["Eo"], df["F"], 1)
    estimated_OOIP = slope
    st.markdown(f"**Estimated OOIP (from slope):** {estimated_OOIP:,.2f} stb")

    st.subheader("⬇️ Export Results")
    df["Estimated OOIP"] = estimated_OOIP
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download MBAL Results (CSV)", csv, "mbal_results.csv", "text/csv")
