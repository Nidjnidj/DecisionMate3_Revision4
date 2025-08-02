import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("rent_buy_title", "Rent vs Buy Decision Tool")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("rent_vs_buy", ""))

    st.subheader(T.get("input_section", "Input Parameters"))

    # Inputs
    years = st.slider(T.get("years", "Analysis Period (Years)"), 1, 30, 10)
    monthly_rent = st.number_input(T.get("monthly_rent", "Monthly Rent"), min_value=0.0, value=1000.0)
    annual_increase_rent = st.number_input(T.get("annual_rent_increase", "Annual Rent Increase (%)"), value=2.0)
    
    purchase_price = st.number_input(T.get("purchase_price", "Purchase Price"), value=250000.0)
    annual_maintenance = st.number_input(T.get("maintenance_cost", "Annual Maintenance Cost"), value=2000.0)
    annual_property_tax = st.number_input(T.get("property_tax", "Annual Property Tax"), value=1500.0)
    annual_appreciation = st.number_input(T.get("appreciation", "Annual Property Appreciation (%)"), value=3.0)

    # Calculations
    rent_costs = []
    buy_costs = []
    rent_total = 0
    buy_total = purchase_price

    rent = monthly_rent * 12
    property_value = purchase_price

    for year in range(1, years + 1):
        rent_total += rent
        property_value *= (1 + annual_appreciation / 100)
        buy_total += annual_maintenance + annual_property_tax
        rent_costs.append(rent_total)
        buy_costs.append(buy_total - property_value)
        rent *= (1 + annual_increase_rent / 100)

    df = pd.DataFrame({
        "Year": list(range(1, years + 1)),
        "Total Rent Cost": rent_costs,
        "Net Buy Cost (Purchase - Value)": buy_costs
    })

    st.subheader(T.get("results_section", "Cost Comparison Table"))
    st.dataframe(df)

    st.subheader(T.get("results_chart", "Rent vs Buy Chart"))
    fig, ax = plt.subplots()
    ax.plot(df["Year"], df["Total Rent Cost"], label="Rent")
    ax.plot(df["Year"], df["Net Buy Cost (Purchase - Value)"], label="Buy")
    ax.set_xlabel("Year")
    ax.set_ylabel("Cumulative Cost")
    ax.set_title("Rent vs Buy Comparison")
    ax.legend()
    st.pyplot(fig)

    # Export to Excel
    excel_file = io.BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)
    st.download_button(T.get("download_excel", "Download Excel"), excel_file,
                       file_name="rent_vs_buy.xlsx", mime="application/vnd.ms-excel")

    # Export to PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True)
    for _, row in df.iterrows():
        pdf.cell(200, 10, txt=f"Year {row['Year']}: Rent=${row['Total Rent Cost']:.2f}, Buy=${row['Net Buy Cost (Purchase - Value)']:.2f}", ln=True)
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                       file_name="rent_vs_buy.pdf", mime="application/pdf")

    # Firebase Save/Load
    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, title, df.to_dict("records"))
        st.success(T.get("save_success", "Data saved."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df)
            st.success(T.get("load_success", "Data loaded."))
        else:
            st.warning(T.get("load_warning", "No saved data found."))

rent_vs_buy = run
