import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "construction_change_tracker"

def construction_change_tracker(T):
    st.subheader("🔄 Construction Change Tracker")

    if "construction_change_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.construction_change_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("change_tracker_form"):
        date = st.date_input("Date", value=datetime.today())
        change_id = st.text_input("Change ID (e.g., CC-001)")
        description = st.text_area("Change Description")
        discipline = st.text_input("Discipline")
        change_type = st.selectbox("Type of Change", ["RFI", "Field Change Notice", "Design Revision", "Change Order"])
        status = st.selectbox("Status", ["Open", "In Progress", "Closed"])
        impact = st.text_area("Impact (Cost / Schedule)")
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Change")
        if submitted:
            st.session_state.construction_change_data.append({
                "Date": str(date),
                "Change ID": change_id,
                "Description": description,
                "Discipline": discipline,
                "Type": change_type,
                "Status": status,
                "Impact": impact,
                "Remarks": remarks
            })
            st.success("✅ Change entry added!")

    if st.session_state.construction_change_data:
        df = pd.DataFrame(st.session_state.construction_change_data)
        st.dataframe(df, use_container_width=True)

        # Save
        if st.button("💾 Save Change Log"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.construction_change_data)
            st.success("✅ Change log saved to Firestore.")

        # Export Excel
        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="change_tracker.xlsx")

        # Export PDF
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
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="change_tracker.pdf")

        # Load
        if st.button("📤 Load Saved Changes"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.construction_change_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Change log loaded from Firestore.")
