import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("financial_analysis_title", "Financial Analysis")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("financial_analysis", ""))

    if "financial_data" not in st.session_state:
        st.session_state.financial_data = []

    st.subheader(T.get("add_cashflow", "Add Yearly Cash Flow Data"))

    year = st.number_input(T.get("year", "Year"), min_value=1, max_value=100, value=1)
    capex = st.number_input(T.get("capex", "CAPEX"), value=0.0)
    opex = st.number_input(T.get("opex", "OPEX"), value=0.0)
    revenue = st.number_input(T.get("revenue", "Revenue"), value=0.0)

    if st.button(T.get("add_year", "Add Year")):
        st.session_state.financial_data.append({
            "Year": year,
            "CAPEX": capex,
            "OPEX": opex,
            "Revenue": revenue,
            "Net Cash Flow": revenue - opex - capex
        })

    df = pd.DataFrame(st.session_state.financial_data)

    if not df.empty:
        df = df.sort_values("Year")
        st.subheader(T.get("cashflow_table", "Cash Flow Table"))
        st.dataframe(df)

        # Financial metrics
        discount_rate = st.number_input(T.get("discount_rate", "Discount Rate (%)"), value=10.0) / 100
        cash_flows = df["Net Cash Flow"].values
        npv = npf.npv(discount_rate, cash_flows)
        irr = npf.irr(cash_flows)
        cumulative_cashflow = np.cumsum(cash_flows)
        payback_period = next((i+1 for i, x in enumerate(cumulative_cashflow) if x >= 0), "N/A")

        st.subheader(T.get("results", "Financial Summary"))
        st.markdown(f"**NPV:** ${npv:,.2f}")
        st.markdown(f"**IRR:** {irr*100:.2f}%")
        st.markdown(f"**Payback Period:** {payback_period} year(s)")

        # Chart
        st.subheader(T.get("cashflow_chart", "Cash Flow Chart"))
        fig, ax = plt.subplots()
        ax.bar(df["Year"], df["Net Cash Flow"])
        ax.set_xlabel("Year")
        ax.set_ylabel("Net Cash Flow")
        ax.set_title("Net Cash Flow by Year")
        st.pyplot(fig)

        # Export to Excel
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(T.get("download_excel", "Download Excel"), towrite,
                           file_name="financial_analysis.xlsx", mime="application/vnd.ms-excel")

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Year']}: Revenue={row['Revenue']}, CAPEX={row['CAPEX']}, OPEX={row['OPEX']}, Net={row['Net Cash Flow']}"
            pdf.cell(200, 10, txt=line, ln=True)
        pdf.cell(200, 10, txt=f"NPV: ${npv:.2f}, IRR: {irr*100:.2f}%, Payback: {payback_period}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="financial_analysis.pdf", mime="application/pdf")

        # Firebase Save/Load
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.financial_data)
            st.success(T.get("save_success", "Data saved successfully."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.financial_data = data
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

financial_analysis = run
