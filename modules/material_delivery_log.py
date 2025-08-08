import streamlit as st
import pandas as pd
from datetime import date
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "material_delivery_log"

def material_delivery_log(T):
    st.subheader("🚚 Material Delivery Log")

    if "delivery_log" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.delivery_log = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("material_delivery_form"):
        delivery_date = st.date_input("Delivery Date", value=date.today())
        material_name = st.text_input("Material Name")
        quantity = st.text_input("Quantity")
        supplier = st.text_input("Supplier")
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Entry")
        if submitted:
            st.session_state.delivery_log.append({
                "Date": str(delivery_date),
                "Material": material_name,
                "Quantity": quantity,
                "Supplier": supplier,
                "Remarks": remarks
            })
            st.success("✅ Delivery entry added.")

    if st.session_state.delivery_log:
        df = pd.DataFrame(st.session_state.delivery_log)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Log"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.delivery_log)
            st.success("✅ Delivery log saved to Firestore.")

        if st.button("📥 Download Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("📄 Download Excel", buffer.getvalue(), file_name="material_delivery_log.xlsx")

        if st.button("📥 Download PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for _, row in df.iterrows():
                for key, val in row.items():
                    pdf.multi_cell(0, 10, f"{key}: {val}", border=0)
                pdf.ln()
            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button("📄 Download PDF", buffer.getvalue(), file_name="material_delivery_log.pdf")

        if st.button("📤 Load Log"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.delivery_log = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Delivery log loaded from Firestore.")
