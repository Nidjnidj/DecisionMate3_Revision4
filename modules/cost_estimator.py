import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("cost_estimator_title", "Cost Estimator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("cost_estimator", ""))

    if "cost_entries" not in st.session_state:
        st.session_state.cost_entries = []

    st.subheader(T.get("add_item", "Add Work Item"))
    item = st.text_input(T.get("item_description", "Description"))
    quantity = st.number_input(T.get("quantity", "Quantity"), min_value=0.0, value=1.0)
    unit_cost = st.number_input(T.get("unit_cost", "Unit Cost ($)"), min_value=0.0, value=0.0)

    if st.button(T.get("add_item_btn", "Add Item")) and item:
        total_cost = quantity * unit_cost
        st.session_state.cost_entries.append({
            "Description": item,
            "Quantity": quantity,
            "Unit Cost": unit_cost,
            "Total Cost": total_cost
        })

    if st.session_state.cost_entries:
        df = pd.DataFrame(st.session_state.cost_entries)
        st.subheader(T.get("cost_table", "Cost Breakdown"))
        st.dataframe(df)
        st.success(T.get("total_cost", "Total Cost") + f": ${df['Total Cost'].sum():,.2f}")

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Description']} | Qty: {row['Quantity']} | Unit: ${row['Unit Cost']} | Total: ${row['Total Cost']}"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="cost_estimate.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.cost_entries)
            st.success(T.get("save_success", "Items saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.cost_entries = data
                st.success(T.get("load_success", "Items loaded."))
            else:
                st.warning(T.get("load_warning", "No saved cost data found."))
def run(T):
    # your UI logic using T (translations)...
    st.title("Cost Estimator")
    st.info("Coming soon...")  # or your real UI
    # return optional data

cost_estimator = run
