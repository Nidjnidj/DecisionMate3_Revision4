import streamlit as st
import pandas as pd

def run(T):
    st.header(T.get("material_estimator_title", "Material Estimator"))
    st.markdown(T.get("descriptions", {}).get("material_estimator", "Estimate construction material needs based on house area."))

    area = st.number_input(T.get("input_area", "Enter Total Built-up Area (m²)"), min_value=20.0, step=5.0)

    if area:
        materials = {
            T.get("bricks", "Bricks (pcs)"): int(area * 55),
            T.get("cement_bags", "Cement (bags)"): int(area * 0.4),
            T.get("sand_m3", "Sand (m³)"): round(area * 0.5, 1),
            T.get("gravel_m3", "Gravel (m³)"): round(area * 0.5, 1),
            T.get("steel_kg", "Steel (kg)"): int(area * 35),
            T.get("tiles_m2", "Tiles (m²)"): round(area * 0.9, 1),
            T.get("paint_liters", "Paint (liters)"): round(area * 0.4, 1)
        }

        df = pd.DataFrame(list(materials.items()), columns=[T.get("material", "Material"), T.get("quantity", "Estimated Quantity")])
        st.subheader(T.get("material_table", "Estimated Materials"))
        st.table(df)

material_estimator = run
