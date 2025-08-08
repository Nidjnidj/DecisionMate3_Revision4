import streamlit as st
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

MODULE_KEY = "Construction Meeting Notes"

def construction_meeting_notes(T):
    st.subheader("📝 " + MODULE_KEY)

    if "meeting_notes" not in st.session_state:
        st.session_state.meeting_notes = []

    with st.form("meeting_notes_form"):
        meeting_date = st.date_input("Meeting Date", value=datetime.today())
        attendees = st.text_area("Attendees")
        agenda = st.text_area("Agenda Points")
        action_items = st.text_area("Action Items")
        notes = st.text_area("Meeting Notes")

        submitted = st.form_submit_button("➕ Add Note")
        if submitted:
            st.session_state.meeting_notes.append({
                "Date": str(meeting_date),
                "Attendees": attendees,
                "Agenda": agenda,
                "Action Items": action_items,
                "Notes": notes
            })
            st.success("✅ Meeting note added.")

    if st.session_state.meeting_notes:
        df = pd.DataFrame(st.session_state.meeting_notes)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Notes"):
            save_project(st.session_state.username, MODULE_KEY, st.session_state.meeting_notes)
            st.success("✅ Meeting notes saved to cloud.")

        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="meeting_notes.xlsx")

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
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="meeting_notes.pdf")

    if st.button("📤 Load Saved Notes"):
        data = load_project_data(st.session_state.username, MODULE_KEY)
        if data:
            st.session_state.meeting_notes = data
            st.success("✅ Meeting notes loaded successfully.")
        else:
            st.warning("⚠️ No saved notes found.")
