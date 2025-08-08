import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "pre_task_planning"

def pre_task_planning(T):
    st.subheader("📝 Pre-Task Planning Module")

    if "pre_task_planning_data" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.pre_task_planning_data = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("pre_task_form"):
        date = st.date_input("Date", value=datetime.today())
        task_name = st.text_input("Task Name")
        location = st.text_input("Location / Area")
        description = st.text_area("Description of Work")
        manpower = st.text_input("Required Manpower")
        equipment = st.text_input("Required Equipment")
        hazards = st.text_area("Potential Hazards")
        controls = st.text_area("Control Measures")
        supervisor = st.text_input("Supervisor Name")

        submitted = st.form_submit_button("➕ Add Task Plan")
        if submitted:
            st.session_state.pre_task_planning_data.append({
                "Date": str(date),
                "Task Name": task_name,
                "Location": location,
                "Description of Work": description,
                "Required Manpower": manpower,
                "Required Equipment": equipment,
                "Potential Hazards": hazards,
                "Control Measures": controls,
                "Supervisor": supervisor
            })
            st.success("✅ Task plan added!")

    if st.session_state.pre_task_planning_data:
        df = pd.DataFrame(st.session_state.pre_task_planning_data)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Task Plans"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.pre_task_planning_data)
            st.success("✅ Task plans saved to Firestore.")

        if st.button("📥 Download as Excel"):
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button("📄 Download Excel", excel_buffer.getvalue(), file_name="pre_task_plans.xlsx")

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
            st.download_button("📄 Download PDF", pdf_buffer.getvalue(), file_name="pre_task_plans.pdf")

        if st.button("📤 Load Saved Task Plans"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.pre_task_planning_data = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Task plans loaded from Firestore.")
