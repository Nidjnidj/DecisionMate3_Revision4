import streamlit as st
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "temporary_works_register"

def temporary_works_register(T):
    st.subheader("🏗️ Temporary Works Register")

    if "temporary_works_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.temporary_works_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("temporary_works_form"):
        date = st.date_input("Date", value=datetime.today())
        description = st.text_area("Description of Temporary Work")
        location = st.text_input("Location")
        responsible_person = st.text_input("Responsible Person")
        design_status = st.selectbox("Design Status", ["Not Started", "In Progress", "Completed"])
        inspection_status = st.selectbox("Inspection Status", ["Pending", "Approved", "Rejected"])
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Entry")
        if submitted:
            st.session_state.temporary_works_data.append({
                "Date": str(date),
                "Description": description,
                "Location": location,
                "Responsible Person": responsible_person,
                "Design Status": design_status,
                "Inspection Status": inspection_status,
                "Remarks": remarks
            })
            st.success("✅ Entry added to register.")

    if st.session_state.temporary_works_data:
        df = pd.DataFrame(st.session_state.temporary_works_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Register"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.temporary_works_data)
            st.success("✅ Register saved to Firestore.")

        if st.button("📥 Download Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("📄 Download Excel", buffer.getvalue(), file_name="temporary_works.xlsx")

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
            st.download_button("📄 Download PDF", buffer.getvalue(), file_name="temporary_works.pdf")

        if st.button("📤 Load Register"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.temporary_works_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Register loaded from Firestore.")
