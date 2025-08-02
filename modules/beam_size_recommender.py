import streamlit as st

def beam_size_recommender(T):
    st.header("📐 " + T.get("beam_size_recommender_title", "Beam Size Recommender"))

    st.markdown("### Input Structural Load and Span to Recommend Beam Size")

    load = st.number_input("Applied Load (kN/m)", min_value=1.0, value=10.0)
    span = st.number_input("Span Length (m)", min_value=1.0, value=4.0)

    if st.button("Recommend Beam Size"):
        # Simplified empirical formula for depth: span/15 for reinforced concrete beams
        recommended_depth_mm = round((span * 1000) / 15)
        recommended_width_mm = round(recommended_depth_mm * 0.5)

        st.success("✅ Recommended Beam Dimensions:")
        st.write(f"**Depth:** {recommended_depth_mm} mm")
        st.write(f"**Width:** {recommended_width_mm} mm")

    st.caption("Note: This is a simplified estimation. Always consult structural design codes.")
