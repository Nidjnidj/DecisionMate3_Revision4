import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

MODULE_KEY = "Punchlist Tracker"

def punchlist_tracker(T):
    st.subheader("📌 " + MODULE_KEY)

    if "punchlist_data" not in st.session_state:
        st.session_state.punchlist_data = []

    with st.form("punchlist_form"):
        item = st.text_input("Punchlist Item")
        location = st.text_input("Location")
        responsible = st.text_input("Responsible Party")
        status = st.selectbox("Status", ["Open", "In Progress", "Closed"])
        due_date = st.date_input("Due Date", value=datetime.today())
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("➕ Add Punchlist Item")
        if submitted:
            st.session_state.punchlist_data.append({
                "Item": item,
                "Location": location,
                "Responsible": responsible,
                "Status": status,
                "Due Date": str(due_date),
                "Notes": notes
            })
            st.success("✅ Punchlist item added.")

    if st.session_state.punchlist_data:
        df = pd.DataFrame(st.session_state.punchlist_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Punchlist"):
            save_project(st.session_state.username, MODULE_KEY, st.session_state.punchlist_data)
            st.success("✅ Punchlist saved to cloud.")

        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="punchlist.xlsx")

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
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="punchlist.pdf")

    if st.button("📤 Load Saved Punchlist"):
        data = load_project_data(st.session_state.username, MODULE_KEY)
        if data:
            st.session_state.punchlist_data = data
            st.success("✅ Punchlist loaded successfully.")
        else:
            st.warning("⚠️ No saved punchlist found.")
