# modules/project_tracker.py

import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("project_tracker_title", "📅 Project Tracker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("project_tracker", "Track project tasks, deadlines, and statuses."))

    if "project_tasks" not in st.session_state:
        st.session_state.project_tasks = []

    st.subheader(T.get("add_task", "➕ Add New Task"))

    task_name = st.text_input(T.get("task_name", "Task Name"))
    assigned_to = st.text_input(T.get("assigned_to", "Assigned To"))
    due_date = st.date_input(T.get("due_date", "Due Date"))
    status = st.selectbox(T.get("status", "Status"), ["Not Started", "In Progress", "Completed", "Blocked"])

    if st.button(T.get("add_task_button", "Add Task")) and task_name:
        st.session_state.project_tasks.append({
            "Task": task_name,
            "Assigned To": assigned_to,
            "Due Date": due_date.strftime("%Y-%m-%d"),
            "Status": status
        })

    if st.session_state.project_tasks:
        df = pd.DataFrame(st.session_state.project_tasks)
        st.subheader(T.get("task_list", "📋 Task List"))
        st.dataframe(df)

        # Excel export
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="project_tasks.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # PDF export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=f"Task: {row['Task']} | Assigned: {row['Assigned To']} | Due: {row['Due Date']} | Status: {row['Status']}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="project_tasks.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.project_tasks)
            st.success(T.get("save_success", "Project saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.project_tasks = data
                st.success(T.get("load_success", "Tasks loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

project_tracker = run
