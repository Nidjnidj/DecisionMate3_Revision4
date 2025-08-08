import streamlit as st
import pandas as pd
from datetime import date
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "construction_equipment_log"

def construction_equipment_log(T):
    st.subheader("🏗️ Construction Equipment Log")

    if "equipment_log" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.equipment_log = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("equipment_log_form"):
        log_date = st.date_input("Date", value=date.today())
        equipment_type = st.text_input("Equipment Type")
        quantity = st.number_input("Quantity", min_value=0, step=1)
        working_hours = st.number_input("Working Hours", min_value=0.0, step=0.5)
        condition = st.selectbox("Condition", ["Good", "Needs Maintenance", "Out of Service"])
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Equipment Entry")
        if submitted:
            st.session_state.equipment_log.append({
                "Date": str(log_date),
                "Equipment Type": equipment_type,
                "Quantity": quantity,
                "Working Hours": working_hours,
                "Condition": condition,
                "Remarks": remarks
            })
            st.success("✅ Equipment record added.")

    if st.session_state.equipment_log:
        df = pd.DataFrame(st.session_state.equipment_log)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Log"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.equipment_log)
            st.success("✅ Equipment log saved to Firestore.")

        if st.button("📥 Download Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("📄 Download Excel", buffer.getvalue(), file_name="equipment_log.xlsx")

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
            st.download_button("📄 Download PDF", buffer.getvalue(), file_name="equipment_log.pdf")

        if st.button("📤 Load Log"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.equipment_log = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Equipment log loaded from Firestore.")
