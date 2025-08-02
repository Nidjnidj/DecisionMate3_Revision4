import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("steel_tracker_title", "Steel Material Tracker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("steel_material_tracker", ""))

    if "steel_entries" not in st.session_state:
        st.session_state.steel_entries = []

    st.subheader(T.get("add_steel", "Add Steel Member"))
    member_type = st.selectbox(T.get("member_type", "Member Type"), ["Beam", "Column", "Angle", "Plate", "Truss"])
    designation = st.text_input(T.get("designation", "Designation (e.g., HEB200)"))
    quantity = st.number_input(T.get("quantity", "Quantity (pcs)"), min_value=1, step=1)
    weight = st.number_input(T.get("weight", "Unit Weight (kg)"), min_value=0.0)
    status = st.selectbox(T.get("fabrication_status", "Fabrication Status"), ["Not Started", "In Fabrication", "Delivered", "Erected"])

    if st.button(T.get("add_steel_btn", "Add Entry")) and designation:
        st.session_state.steel_entries.append({
            "Type": member_type,
            "Designation": designation,
            "Quantity": quantity,
            "Unit Weight (kg)": weight,
            "Status": status
        })

    if st.session_state.steel_entries:
        df = pd.DataFrame(st.session_state.steel_entries)
        df["Total Weight (kg)"] = df["Quantity"] * df["Unit Weight (kg)"]
        st.subheader(T.get("steel_log_table", "Tracked Steel"))
        st.dataframe(df)
        st.success(T.get("total_weight", "Total Weight") + f": {df['Total Weight (kg)'].sum():,.2f} kg")

        # Export PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=(
                f"{row['Type']} {row['Designation']} | Qty: {row['Quantity']} | Weight: {row['Unit Weight (kg)']} kg | Status: {row['Status']}"), ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="steel_tracker.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.steel_entries)
            st.success(T.get("save_success", "Steel data saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.steel_entries = data
                st.success(T.get("load_success", "Steel data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

steel_material_tracker = run
