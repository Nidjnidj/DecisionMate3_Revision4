import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data
import matplotlib.pyplot as plt

def run(T):
    title = T.get("separator_sim_title", "Separator Simulation Tool")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("separator_sim", ""))

    st.subheader(T.get("feed_conditions", "Feed Stream Conditions"))

    total_feed = st.number_input(T.get("total_feed", "Total Feed Flowrate (kg/h)"), min_value=1.0, value=10000.0)
    gas_frac = st.slider(T.get("gas_fraction", "Gas Fraction (wt%)"), 0.0, 100.0, 40.0)
    liq_frac = 100.0 - gas_frac

    st.subheader(T.get("split_efficiency", "Separation Efficiency (ideal = 100%)"))
    gas_eff = st.slider(T.get("gas_efficiency", "Gas Outlet Efficiency (%)"), 50.0, 100.0, 98.0)
    liq_eff = st.slider(T.get("liq_efficiency", "Liquid Outlet Efficiency (%)"), 50.0, 100.0, 95.0)

    if st.button(T.get("simulate", "Run Simulation")):
        feed_gas = total_feed * (gas_frac / 100)
        feed_liq = total_feed * (liq_frac / 100)

        out_gas = feed_gas * (gas_eff / 100)
        out_liq = feed_liq * (liq_eff / 100)

        losses = total_feed - (out_gas + out_liq)

        result = {
            "Feed Gas (kg/h)": round(feed_gas, 2),
            "Feed Liquid (kg/h)": round(feed_liq, 2),
            "Gas Outlet (kg/h)": round(out_gas, 2),
            "Liquid Outlet (kg/h)": round(out_liq, 2),
            "Losses (kg/h)": round(losses, 2)
        }

        df = pd.DataFrame(list(result.items()), columns=["Stream", "Flowrate (kg/h)"])
        st.subheader(T.get("results", "Simulation Results"))
        st.dataframe(df)

        # Pie Chart
        st.subheader(T.get("distribution_chart", "Separator Outlet Distribution"))
        fig, ax = plt.subplots()
        ax.pie([out_gas, out_liq, losses],
               labels=[T.get("gas", "Gas"), T.get("liquid", "Liquid"), T.get("losses", "Losses")],
               autopct='%1.1f%%', startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="separator_simulation.xlsx",
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
                           file_name="separator_simulation.pdf", mime="application/pdf")

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

separator_sim = run
