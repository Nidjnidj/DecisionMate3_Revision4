import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("break_even_title", "Break-Even Calculator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("break_even", ""))

    # Inputs
    st.subheader(T.get("input_section", "Input Parameters"))
    fixed_costs = st.number_input(T.get("fixed_costs", "Fixed Costs"), min_value=0.0, value=50000.0)
    variable_cost_per_unit = st.number_input(T.get("variable_cost", "Variable Cost per Unit"), min_value=0.0, value=50.0)
    price_per_unit = st.number_input(T.get("price_per_unit", "Price per Unit"), min_value=0.0, value=100.0)
    max_units = st.slider(T.get("max_units", "Maximum Units for Plot"), min_value=100, max_value=10000, value=1000)

    if price_per_unit <= variable_cost_per_unit:
        st.error(T.get("price_error", "Price per unit must be greater than variable cost per unit."))
        return

    # Calculations
    break_even_units = fixed_costs / (price_per_unit - variable_cost_per_unit)
    st.subheader(T.get("results", "Results"))
    st.success(f"{T.get('break_even_point', 'Break-even Point')}: {break_even_units:.2f} units")

    units = np.arange(0, max_units + 1)
    revenue = units * price_per_unit
    total_cost = fixed_costs + units * variable_cost_per_unit

    # Plot
    st.subheader(T.get("plot", "Break-Even Chart"))
    fig, ax = plt.subplots()
    ax.plot(units, revenue, label=T.get("revenue", "Revenue"))
    ax.plot(units, total_cost, label=T.get("total_cost", "Total Cost"))
    ax.axvline(break_even_units, color='red', linestyle='--', label=T.get("break_even", "Break-even Point"))
    ax.set_xlabel("Units")
    ax.set_ylabel("Cost / Revenue")
    ax.set_title("Break-Even Analysis")
    ax.legend()
    st.pyplot(fig)

    # PDF Export
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=title, ln=True)
    pdf.cell(200, 10, txt=f"Fixed Costs: ${fixed_costs}", ln=True)
    pdf.cell(200, 10, txt=f"Variable Cost per Unit: ${variable_cost_per_unit}", ln=True)
    pdf.cell(200, 10, txt=f"Price per Unit: ${price_per_unit}", ln=True)
    pdf.cell(200, 10, txt=f"Break-even Point: {break_even_units:.2f} units", ln=True)
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                       file_name="break_even.pdf", mime="application/pdf")

    # Firebase Save/Load
    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, title, {
            "fixed_costs": fixed_costs,
            "variable_cost_per_unit": variable_cost_per_unit,
            "price_per_unit": price_per_unit,
            "break_even_units": break_even_units
        })
        st.success(T.get("save_success", "Data saved."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            st.write(data)
            st.success(T.get("load_success", "Data loaded."))
        else:
            st.warning(T.get("load_warning", "No saved data found."))

break_even = run
