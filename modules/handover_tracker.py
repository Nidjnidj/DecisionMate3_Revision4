import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

MODULE_KEY = "Handover Tracker"

def handover_tracker(T):
    st.subheader("🗂️ " + MODULE_KEY)

    if "handover_data" not in st.session_state:
        st.session_state.handover_data = []

    with st.form("handover_form"):
        handover_date = st.date_input("Handover Date", value=datetime.today())
        area = st.text_input("Area / System")
        discipline = st.text_input("Discipline")
        documents = st.text_area("Documents Submitted")
        outstanding = st.text_area("Outstanding Items")
        status = st.selectbox("Handover Status", ["Pending", "Partial", "Complete", "Rejected"])
        accepted_by = st.text_input("Accepted By")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("➕ Add Handover Entry")
        if submitted:
            st.session_state.handover_data.append({
                "Handover Date": str(handover_date),
                "Area / System": area,
                "Discipline": discipline,
                "Documents Submitted": documents,
                "Outstanding Items": outstanding,
                "Status": status,
                "Accepted By": accepted_by,
                "Notes": notes
            })
            st.success("✅ Handover entry added!")

    if st.session_state.handover_data:
        df = pd.DataFrame(st.session_state.handover_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Handover Log"):
            save_project(st.session_state.username, MODULE_KEY, st.session_state.handover_data)
            st.success("✅ Handover log saved to cloud.")

        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="handover_log.xlsx")

        if st.button("📥 Download as PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for i, row in df.iterrows():
                for key, val in row.items():
                    pdf.multi_cell(0, 10, f"{key}: {val}", border=0)
                pdf.ln()
            pdf_buffer = io.BytesIO()
            pdf.output(pdf_buffer)
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="handover_log.pdf")

    if st.button("📤 Load Saved Handover Log"):
        data = load_project_data(st.session_state.username, MODULE_KEY)
        if data:
            st.session_state.handover_data = data
            st.success("✅ Handover log loaded successfully.")
        else:
            st.warning("⚠️ No saved handover log found.")
