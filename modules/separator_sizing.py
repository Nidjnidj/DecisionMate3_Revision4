import streamlit as st
import pandas as pd
import math
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("separator_sizing_title", "Separator Sizing Tool")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("separator_sizing", ""))

    st.subheader(T.get("input_parameters", "Input Parameters"))

    separator_type = st.radio(T.get("separator_type", "Separator Type"), ["Horizontal", "Vertical"])
    gas_rate = st.number_input(T.get("gas_rate", "Gas Flowrate (MMSCFD)"), min_value=0.1, value=10.0)
    liquid_rate = st.number_input(T.get("liquid_rate", "Liquid Flowrate (m3/h)"), min_value=0.1, value=50.0)
    pressure = st.number_input(T.get("pressure", "Operating Pressure (bar)"), min_value=1.0, value=20.0)
    temperature = st.number_input(T.get("temperature", "Temperature (°C)"), value=40.0)

    if st.button(T.get("calculate", "Calculate")):
        # Simplified sizing using API 12J heuristics

        # Convert gas rate to m3/s (1 MMSCFD ≈ 327.74 m3/h)
        gas_m3h = gas_rate * 327.74
        gas_m3s = gas_m3h / 3600
        liq_m3s = liquid_rate / 3600

        # Suggested gas velocity for separation (m/s)
        vg = 0.1 if separator_type == "Horizontal" else 0.05

        # Vessel cross-sectional area for gas separation
        A = gas_m3s / vg
        D = math.sqrt((4 * A) / math.pi)

        # Vessel length (for horizontal): 3 × diameter min
        L = D * 3 if separator_type == "Horizontal" else D * 4

        # Internal volume (cylindrical only)
        volume = (math.pi / 4) * D**2 * L

        result = {
            "Separator Type": separator_type,
            "Gas Flowrate (m3/s)": round(gas_m3s, 2),
            "Liquid Flowrate (m3/s)": round(liq_m3s, 2),
            "Required Diameter (m)": round(D, 2),
            "Length (m)": round(L, 2),
            "Volume (m³)": round(volume, 2)
        }

        df = pd.DataFrame(list(result.items()), columns=["Parameter", "Value"])
        st.subheader(T.get("results", "Sizing Results"))
        st.dataframe(df)

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="separator_sizing.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            pdf.cell(200, 10, txt=f"{df.iloc[i, 0]}: {df.iloc[i, 1]}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="separator_sizing.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, result)
            st.success(T.get("save_success", "Project saved successfully."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.json(data)
            else:
                st.warning(T.get("load_warning", "No saved data found."))

separator_sizing = run
