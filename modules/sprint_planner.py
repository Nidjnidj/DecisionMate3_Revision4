import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("sprint_planner_title", "Sprint Planner")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("sprint_planner", ""))

    st.subheader(T.get("sprint_details", "Sprint Details"))
    sprint_name = st.text_input(T.get("sprint_name", "Sprint Name"))
    sprint_duration = st.number_input(T.get("sprint_duration", "Sprint Duration (days)"), min_value=1, value=14)

    st.subheader(T.get("add_tasks", "Add Tasks to Sprint"))
    task = st.text_input(T.get("task_name", "Task"))
    assignee = st.text_input(T.get("assignee", "Assignee"))
    story_points = st.number_input(T.get("story_points", "Story Points"), min_value=1, value=3)

    if "sprint_tasks" not in st.session_state:
        st.session_state.sprint_tasks = []

    if st.button(T.get("add_task", "Add Task")) and task:
        st.session_state.sprint_tasks.append({
            "Task": task,
            "Assignee": assignee,
            "Story Points": story_points
        })

    df = pd.DataFrame(st.session_state.sprint_tasks)

    if not df.empty:
        st.subheader(T.get("sprint_board", "Sprint Task Board"))
        st.dataframe(df)

        total_points = df["Story Points"].sum()
        st.markdown(f"**{T.get('total_story_points', 'Total Story Points')}: {total_points}**")

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="sprint_tasks.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title + " - " + sprint_name, ln=True)
        for i in range(len(df)):
            row = df.iloc[i]
            pdf.cell(200, 10, txt=f"{row['Task']} - {row['Assignee']} - {row['Story Points']} pts", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="sprint_tasks.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title + " - " + sprint_name, df.to_dict())
            st.success(T.get("save_success", "Sprint saved successfully."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title + " - " + sprint_name)
            if data:
                df_loaded = pd.DataFrame(data)
                st.session_state.sprint_tasks = df_loaded.to_dict(orient='records')
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

sprint_planner = run
