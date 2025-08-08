import streamlit as st
import math

def run(T):
    st.title("📊 Process Capability Calculator (Cp, Cpk)")

    st.markdown("""
    This tool calculates Cp and Cpk based on your process data.
    - **Cp** indicates potential process capability.
    - **Cpk** shows actual process performance relative to target.
    """)

    st.subheader("🔢 Input Data")

    usl = st.number_input("Upper Specification Limit (USL)", step=0.01)
    lsl = st.number_input("Lower Specification Limit (LSL)", step=0.01)
    mean = st.number_input("Process Mean (μ)", step=0.01)
    std_dev = st.number_input("Standard Deviation (σ)", step=0.01)

    if st.button("📈 Calculate Cp & Cpk"):
        if std_dev > 0 and usl > lsl:
            cp = (usl - lsl) / (6 * std_dev)
            cpk = min((usl - mean), (mean - lsl)) / (3 * std_dev)

            st.success("✅ Calculation Complete")
            st.metric("Cp (Capability)", f"{cp:.3f}")
            st.metric("Cpk (Performance)", f"{cpk:.3f}")

            if cp < 1 or cpk < 1:
                st.warning("⚠️ Your process may not be capable. Consider improvement actions.")
            else:
                st.success("🎯 Your process is statistically capable.")
        else:
            st.error("❌ Please ensure LSL < USL and Standard Deviation > 0.")
