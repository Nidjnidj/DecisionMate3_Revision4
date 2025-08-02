import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from fpdf import FPDF
import io
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T["burndown_chart_title"])
    st.markdown(T["descriptions"].get("burndown_chart", ""))

    st.subheader(T.get("sprint_settings", "Sprint Settings"))
    sprint_name = st.text_input(T.get("sprint_name", "Sprint Name"), value="Sprint 1")
    sprint_days = st.number_input(T.get("sprint_duration", "Sprint Duration (days)"), min_value=1, max_value=30, value=7)
    total_tasks = st.number_input(T.get("total_tasks", "Total Tasks in Sprint"), min_value=1, value=20)

    st.subheader(T.get("progress_tracking", "Track Daily Completion"))
    completed = []
    for i in range(sprint_days):
        completed_tasks = st.number_input(
            f"{T.get('day', 'Day')} {i+1} {T.get('completed_tasks', 'Completed Tasks')}",
            min_value=0, value=0, step=1, key=f"c_{i}"
        )
        completed.append(completed_tasks)

    df = pd.DataFrame({
        T.get("day", "Day"): list(range(1, sprint_days+1)),
        T.get("actual_remaining", "Actual Remaining"): [total_tasks - sum(completed[:i+1]) for i in range(sprint_days)],
        T.get("ideal_remaining", "Ideal Remaining"): [total_tasks - i*(total_tasks//(sprint_days-1)) for i in range(sprint_days)]
    })

    st.subheader(T.get("burndown_graph", "Burndown Chart"))
    fig = px.line(df, x=T.get("day", "Day"), y=[T.get("actual_remaining", "Actual Remaining"), T.get("ideal_remaining", "Ideal Remaining")],
                  markers=True, title=T["burndown_chart_title"])
    st.plotly_chart(fig)

    # Export PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"{T['burndown_chart_title']} - {sprint_name}", ln=True)
    for i in range(sprint_days):
        pdf.cell(200, 10, txt=f"Day {i+1}: Actual Remaining {df.iloc[i,1]}, Ideal Remaining {df.iloc[i,2]}", ln=True)
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T["download_pdf"], data=pdf_output, file_name="burndown_chart.pdf", mime="application/pdf")

    if st.button(T["save"]):
        save_project(st.session_state.username, f"{T['burndown_chart_title']} - {sprint_name}", df.to_dict())
        st.success(T["save_success"])

    if st.button(T["load"]):
        saved = load_project_data(st.session_state.username, f"{T['burndown_chart_title']} - {sprint_name}")
        if saved:
            st.json(saved)
        else:
            st.warning(T["load_warning"])

burndown_chart = run
