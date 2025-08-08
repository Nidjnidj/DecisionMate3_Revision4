import streamlit as st
import pandas as pd
from datetime import date
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "manpower_tracker"

def manpower_tracker(T):
    st.subheader("👷 Manpower Tracker")

    if "manpower_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.manpower_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("manpower_form"):
        entry_date = st.date_input("Date", value=date.today())
        trade = st.text_input("Trade/Discipline")
        workers_count = st.number_input("Number of Workers", min_value=0, step=1)
        contractor = st.text_input("Contractor Name")
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Record")
        if submitted:
            st.session_state.manpower_data.append({
                "Date": str(entry_date),
                "Trade": trade,
                "Workers": workers_count,
                "Contractor": contractor,
                "Remarks": remarks
            })
            st.success("✅ Record added.")

    if st.session_state.manpower_data:
        df = pd.DataFrame(st.session_state.manpower_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Data"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.manpower_data)
            st.success("✅ Data saved to Firestore.")

        if st.button("📥 Download Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("📄 Download Excel", buffer.getvalue(), file_name="manpower_tracker.xlsx")

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
            st.download_button("📄 Download PDF", buffer.getvalue(), file_name="manpower_tracker.pdf")

        if st.button("📤 Load Data"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.manpower_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Data loaded from Firestore.")
