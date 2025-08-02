import streamlit as st
import pandas as pd
import datetime
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("goal_planner_title", "Goal Planner")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("goal_planner", ""))

    if "goals" not in st.session_state:
        st.session_state.goals = []

    st.subheader(T.get("add_goal", "Add New Goal"))

    goal_name = st.text_input(T.get("goal_name", "Goal Name"))
    step = st.text_input(T.get("goal_step", "Step Description"))
    deadline = st.date_input(T.get("deadline", "Deadline"), min_value=datetime.date.today())
    priority = st.selectbox(T.get("priority", "Priority"), ["Low", "Medium", "High"])
    status = st.selectbox(T.get("status", "Status"), ["Planned", "In Progress", "Completed"])

    if st.button(T.get("add_step", "Add Step")) and goal_name and step:
        st.session_state.goals.append({
            "Goal": goal_name,
            "Step": step,
            "Deadline": str(deadline),
            "Priority": priority,
            "Status": status
        })

    if st.session_state.goals:
        df = pd.DataFrame(st.session_state.goals)
        st.subheader(T.get("goal_list", "Planned Goals"))
        st.dataframe(df)

        # Summary
        st.markdown("### 📊 " + T.get("summary", "Summary"))
        status_counts = df["Status"].value_counts()
        for s, count in status_counts.items():
            st.write(f"{s}: {count}")

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Goal']} - {row['Step']} | {row['Deadline']} | {row['Priority']} | {row['Status']}"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="goal_planner.pdf", mime="application/pdf")

        # Firebase Save/Load
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.goals)
            st.success(T.get("save_success", "Goals saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.goals = data
                st.success(T.get("load_success", "Goals loaded."))
            else:
                st.warning(T.get("load_warning", "No saved goals found."))

goal_planner = run
