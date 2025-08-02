import streamlit as st
import pandas as pd
import io
from fpdf import FPDF

def run(T):
    st.title("⚡ Power Demand Calculator")
    st.markdown("Estimate total electrical power demand based on your inputs.")

    if "devices" not in st.session_state:
        st.session_state.devices = []

    st.subheader("➕ Add Device/System")
    name = st.text_input("Device Name")
    quantity = st.number_input("Quantity", min_value=1, value=1)
    power_rating = st.number_input("Power per unit (W)", min_value=0.0, value=100.0)
    hours = st.number_input("Usage per day (hours)", min_value=0.0, value=1.0)

    if st.button("Add to List") and name:
        st.session_state.devices.append({
            "Device": name,
            "Quantity": quantity,
            "Power (W)": power_rating,
            "Daily Usage (hr)": hours,
            "Total Power (W)": quantity * power_rating,
            "Energy (Wh/day)": quantity * power_rating * hours
        })

    if st.session_state.devices:
        df = pd.DataFrame(st.session_state.devices)
        st.subheader("📋 Power Demand Summary")
        st.dataframe(df)

        total_kw = df["Total Power (W)"].sum() / 1000
        total_kwh = df["Energy (Wh/day)"].sum() / 1000
        st.success(f"🔌 Total Demand: {total_kw:.2f} kW")
        st.success(f"⚡ Daily Consumption: {total_kwh:.2f} kWh")

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Power Demand Report", ln=True)
        for _, row in df.iterrows():
            line = f"{row['Device']} | Qty: {row['Quantity']} | Power: {row['Power (W)']}W | Usage: {row['Daily Usage (hr)']}h"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf.cell(200, 10, txt=f"Total Power: {total_kw:.2f} kW", ln=True)
        pdf.cell(200, 10, txt=f"Total Energy: {total_kwh:.2f} kWh/day", ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button("📄 Download PDF", pdf_output, file_name="power_demand.pdf", mime="application/pdf")

power_demand = run
