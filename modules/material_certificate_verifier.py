import streamlit as st
import pandas as pd

def run(T):
    st.title("📄 Material Certificate Verifier")

    st.markdown("""
    Verify key properties of material test certificates (MTC)  
    against required specifications.
    """)

    st.subheader("📥 Enter Material Certificate Details")

    heat_number = st.text_input("Heat Number")
    material_grade = st.text_input("Material Grade")
    yield_strength = st.number_input("Yield Strength (MPa)", min_value=0.0, step=1.0)
    tensile_strength = st.number_input("Tensile Strength (MPa)", min_value=0.0, step=1.0)
    spec_yield = st.number_input("Required Min Yield Strength (MPa)", min_value=0.0, step=1.0)
    spec_tensile = st.number_input("Required Min Tensile Strength (MPa)", min_value=0.0, step=1.0)

    if st.button("✅ Verify"):
        yield_pass = yield_strength >= spec_yield
        tensile_pass = tensile_strength >= spec_tensile

        if yield_pass and tensile_pass:
            st.success("✅ Material meets the specification.")
        else:
            st.error("❌ Material does NOT meet specification.")
            if not yield_pass:
                st.warning("⚠️ Yield strength is below required spec.")
            if not tensile_pass:
                st.warning("⚠️ Tensile strength is below required spec.")

        st.markdown("### 📋 Summary")
        st.write({
            "Heat Number": heat_number,
            "Grade": material_grade,
            "Yield Strength (MPa)": yield_strength,
            "Tensile Strength (MPa)": tensile_strength
        })
