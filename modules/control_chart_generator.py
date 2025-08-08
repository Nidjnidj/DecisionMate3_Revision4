import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

def run(T):
    st.title("📉 Control Chart Generator")

    st.markdown("""
    Upload or input sample data to generate a control chart.
    - Calculates the **mean (X̄)**, **Upper Control Limit (UCL)**, and **Lower Control Limit (LCL)**.
    - Helps monitor process stability over time.
    """)

    st.subheader("📥 Data Input")

    data_str = st.text_area("Enter sample values separated by commas", value="10,12,11,13,12,14,15,13,12,11,13,14")
    try:
        data = np.array([float(x.strip()) for x in data_str.split(",") if x.strip() != ""])

        if len(data) < 3:
            st.error("Please enter at least 3 data points.")
            return

        x_bar = np.mean(data)
        sigma = np.std(data, ddof=1)
        ucl = x_bar + 3 * sigma
        lcl = x_bar - 3 * sigma

        st.success(f"✅ X̄: {x_bar:.2f}, σ: {sigma:.2f}")
        st.info(f"Control Limits → UCL: {ucl:.2f}, LCL: {lcl:.2f}")

        # Plot
        fig, ax = plt.subplots()
        ax.plot(data, marker='o', label='Data')
        ax.axhline(x_bar, color='blue', linestyle='--', label='X̄ (Mean)')
        ax.axhline(ucl, color='red', linestyle='--', label='UCL (+3σ)')
        ax.axhline(lcl, color='red', linestyle='--', label='LCL (-3σ)')
        ax.set_title("X̄ Control Chart")
        ax.set_xlabel("Sample Index")
        ax.set_ylabel("Value")
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error("Invalid input. Please enter numeric values only.")
        st.exception(e)
