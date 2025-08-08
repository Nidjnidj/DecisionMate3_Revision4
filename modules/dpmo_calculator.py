import streamlit as st
import math

def run(T):
    st.title("📏 DPMO & Sigma Level Calculator")

    st.markdown("""
    Use this tool to calculate:
    - **DPMO** (Defects Per Million Opportunities)
    - **Sigma Level** (Process Performance Index)
    """)

    st.subheader("📥 Input Values")

    try:
        units = st.number_input("Number of Units Inspected", min_value=1, step=1)
        defects = st.number_input("Total Defects Found", min_value=0, step=1)
        opportunities = st.number_input("Opportunities per Unit", min_value=1, step=1)

        if st.button("📊 Calculate DPMO & Sigma"):
            total_opportunities = units * opportunities
            if total_opportunities == 0:
                st.error("Opportunities cannot be zero.")
                return

            dpmo = (defects / total_opportunities) * 1_000_000

            # Approximate sigma level using short-cut formula (not exact normal distribution)
            sigma_level = 1.5 + (math.sqrt(2) * math.erfcinv(dpmo / 1_000_000 * 2))

            st.metric("DPMO", f"{dpmo:.2f}")
            st.metric("Approx. Sigma Level", f"{sigma_level:.2f}")

            if sigma_level < 3:
                st.warning("⚠️ Your process is below industry standard.")
            elif sigma_level >= 6:
                st.success("🎯 Excellent! You’ve achieved Six Sigma quality.")
            else:
                st.info("✅ Your process is acceptable, but may still be improved.")
    except Exception as e:
        st.error("An error occurred during calculation.")
        st.exception(e)
