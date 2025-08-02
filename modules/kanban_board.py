import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("kanban_board_title", "Kanban Task Board")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("kanban_board", ""))

    if "kanban_data" not in st.session_state:
        st.session_state.kanban_data = {
            "To Do": [],
            "In Progress": [],
            "Done": []
        }

    st.subheader(T.get("add_task", "Add New Task"))
    task = st.text_input(T.get("task_name", "Task Name"))
    status = st.selectbox(T.get("select_status", "Select Status"), ["To Do", "In Progress", "Done"])

    if st.button(T.get("add_to_board", "Add to Board")) and task:
        st.session_state.kanban_data[status].append(task)

    st.subheader(T.get("task_board", "Task Board"))

    col1, col2, col3 = st.columns(3)
    columns = ["To Do", "In Progress", "Done"]
    cols = [col1, col2, col3]

    for col, status in zip(cols, columns):
        col.markdown(f"### {status}")
        for i, task in enumerate(st.session_state.kanban_data[status]):
            col.markdown(f"- {task}")

    # Export
    flat_data = []
    for status, tasks in st.session_state.kanban_data.items():
        for t in tasks:
            flat_data.append({"Task": t, "Status": status})
    df = pd.DataFrame(flat_data)

    if not df.empty:
        st.subheader(T.get("export", "Export Options"))

        # Excel
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="kanban_tasks.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            pdf.cell(200, 10, txt=f"{df.iloc[i, 0]} - {df.iloc[i, 1]}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="kanban_tasks.pdf", mime="application/pdf")

        # Firebase
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.kanban_data)
            st.success(T.get("save_success", "Kanban board saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.kanban_data = data
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

kanban_board = run
