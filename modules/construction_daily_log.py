import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "construction_daily_log"

def construction_daily_log(T):
    st.subheader("📅 Construction Daily Log")

    if "construction_daily_log_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.construction_daily_log_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("daily_log_form"):
        date = st.date_input("Date", value=datetime.today())
        weather = st.selectbox("Weather", ["Sunny", "Cloudy", "Rainy", "Windy", "Snowy", "Stormy"])
        work_done = st.text_area("Work Completed")
        labor = st.text_input("Labor Used (e.g., 12 workers)")
        equipment = st.text_input("Equipment Used")
        safety = st.text_area("Safety Issues")
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Entry")
        if submitted:
            st.session_state.construction_daily_log_data.append({
                "Date": str(date),
                "Weather": weather,
                "Work Completed": work_done,
                "Labor Used": labor,
                "Equipment Used": equipment,
                "Safety Issues": safety,
                "Remarks": remarks
            })
            st.success("✅ Entry added!")

    # Display current log
    if st.session_state.construction_daily_log_data:
        df = pd.DataFrame(st.session_state.construction_daily_log_data)
        st.dataframe(df, use_container_width=True)

        # Save to Firestore
        if st.button("💾 Save Log"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.construction_daily_log_data)
            st.success("✅ Log saved to Firestore.")

        # Download Excel
        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="daily_log.xlsx")

        # Download PDF
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
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="daily_log.pdf")

        # Reload
        if st.button("📤 Load Saved Log"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.construction_daily_log_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Log loaded from Firestore.")
