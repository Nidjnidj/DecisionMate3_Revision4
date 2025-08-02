import streamlit as st

def run(T):
    title = T.get("foundation_selector_title", "Foundation Type Selector")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("foundation_selector", ""))

    st.subheader(T.get("foundation_input", "Input Parameters"))

    soil_type = st.selectbox(T.get("soil_type", "Soil Type"), [
        "Loose Sand", "Medium Sand", "Dense Sand",
        "Soft Clay", "Stiff Clay", "Rock", "Mixed Fill"])

    structure_type = st.selectbox(T.get("structure_type", "Structure Type"), [
        "Residential", "Commercial", "Industrial", "Tower", "Bridge"])

    load = st.number_input(T.get("load_applied", "Total Load (kN)"), min_value=0.0, value=100.0)
    water_table = st.selectbox(T.get("water_table", "Water Table Level"), ["Low", "Moderate", "High"])

    if st.button(T.get("suggest_btn", "Suggest Foundation Type")):
        suggestion = "Shallow Foundation"

        if soil_type in ["Loose Sand", "Soft Clay", "Mixed Fill"] or load > 1000 or water_table == "High":
            suggestion = "Deep Foundation (Piles, Caissons)"
        elif soil_type == "Rock" and load < 1000:
            suggestion = "Spread Footing on Rock"

        st.success(T.get("recommended", "Recommended Foundation Type") + f": {suggestion}")

foundation_selector = run
