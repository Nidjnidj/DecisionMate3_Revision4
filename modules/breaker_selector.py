import streamlit as st

def run(T):
    st.title("⚡ Breaker & Fuse Selector")
    st.markdown("This tool helps determine an appropriate breaker or fuse rating for a given load.")

    current = st.number_input("Nominal Load Current (A)", min_value=0.0, value=16.0)
    safety_margin = st.slider("Safety Margin (%)", 0, 100, 25)

    if st.button("🔍 Recommend Breaker"):
        if current == 0:
            st.warning("Current must be greater than zero.")
            return

        adjusted_current = current * (1 + safety_margin / 100)

        # Round to standard breaker sizes
        standard_sizes = [6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400]
        recommended = next((size for size in standard_sizes if size >= adjusted_current), None)

        if recommended:
            st.success(f"✅ Recommended Breaker/Fuse Size: {recommended} A")
        else:
            st.error("⚠️ Load too high for standard breaker sizes. Consider specialized protection.")

breaker_selector = run
