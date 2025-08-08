import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "qc_inspection_checklist"

def qc_inspection_checklist(T):
    st.subheader("✅ QC Inspection Checklist")

    if "qc_inspection_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.qc_inspection_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("qc_checklist_form"):
        date = st.date_input("Date", value=datetime.today())
        checklist_type = st.selectbox("Checklist Type", ["Civil", "Structural", "Mechanical", "Electrical", "Piping", "Welding"])
        activity = st.text_input("Activity / Item")
        result = st.selectbox("Result", ["Pass", "Fail", "N/A"])
        comments = st.text_area("Comments")
        inspector = st.text_input("Inspector Name")

        submitted = st.form_submit_button("➕ Add Record")
        if submitted:
            st.session_state.qc_inspection_data.append({
                "Date": str(date),
                "Checklist Type": checklist_type,
                "Activity / Item": activity,
                "Result": result,
                "Comments": comments,
                "Inspector": inspector
            })
            st.success("✅ Record added!")

    if st.session_state.qc_inspection_data:
        df = pd.DataFrame(st.session_state.qc_inspection_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Checklist"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.qc_inspection_data)
            st.success("✅ Checklist saved to Firestore.")

        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="qc_checklist.xlsx")

        if st.button("📥 Download as PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for _, row in df.iterrows():
                for key, val in row.items():
                    pdf.multi_cell(0, 10, f"{key}: {val}", border=0)
                pdf.ln()
            pdf_buffer = io.BytesIO()
            pdf.output(pdf_buffer)
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="qc_checklist.pdf")

        if st.button("📤 Load Saved Checklist"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.qc_inspection_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Checklist loaded from Firestore.")
