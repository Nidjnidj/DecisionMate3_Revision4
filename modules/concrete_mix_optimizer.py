import streamlit as st

def concrete_mix_optimizer(T):
    st.header("🧱 " + T.get("concrete_mix_optimizer_title", "Concrete Mix Optimizer"))

    st.markdown("### Input Desired Concrete Strength & Mix Parameters")

    fck = st.number_input("Target Concrete Strength (MPa)", min_value=10.0, value=30.0)
    w_c_ratio = st.slider("Water-Cement Ratio", min_value=0.3, max_value=0.6, value=0.45)
    sand_percent = st.slider("Sand (% of total aggregate)", min_value=30, max_value=50, value=40)
    coarse_percent = 100 - sand_percent

    if st.button("Optimize Mix"):
        cement = round((fck * 0.5) / w_c_ratio, 2)
        water = round(cement * w_c_ratio, 2)
        fine_agg = round(cement * sand_percent / 100 * 1.5, 2)
        coarse_agg = round(cement * coarse_percent / 100 * 1.5, 2)

        st.success("✅ Recommended Mix Proportions (per m³):")
        st.write(f"**Cement:** {cement} kg")
        st.write(f"**Water:** {water} kg")
        st.write(f"**Fine Aggregate (Sand):** {fine_agg} kg")
        st.write(f"**Coarse Aggregate:** {coarse_agg} kg")

    st.caption("Note: Simplified empirical method. For structural applications, follow design codes.")
