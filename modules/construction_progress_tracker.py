import streamlit as st
import pandas as pd
from datetime import date
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "construction_progress_tracker"

def construction_progress_tracker(T):
    st.subheader("📈 Construction Progress Tracker")

    if "progress_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.progress_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("progress_form"):
        entry_date = st.date_input("Date", value=date.today())
        activity = st.text_input("Construction Activity")
        planned_progress = st.number_input("Planned %", min_value=0.0, max_value=100.0, step=1.0)
        actual_progress = st.number_input("Actual %", min_value=0.0, max_value=100.0, step=1.0)
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Entry")
        if submitted:
            st.session_state.progress_data.append({
                "Date": str(entry_date),
                "Activity": activity,
                "Planned Progress (%)": planned_progress,
                "Actual Progress (%)": actual_progress,
                "Remarks": remarks
            })
            st.success("✅ Progress entry added.")

    if st.session_state.progress_data:
        df = pd.DataFrame(st.session_state.progress_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Progress"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.progress_data)
            st.success("✅ Progress data saved to Firestore.")

        if st.button("📥 Download Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("📄 Download Excel", buffer.getvalue(), file_name="construction_progress.xlsx")

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
            st.download_button("📄 Download PDF", buffer.getvalue(), file_name="construction_progress.pdf")

        if st.button("📤 Load Progress"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.progress_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Progress data loaded from Firestore.")
