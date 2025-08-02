import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("schedule_developer_title", "Simple Schedule Developer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("schedule_developer", ""))

    if "schedule_data" not in st.session_state:
        st.session_state.schedule_data = []

    st.subheader(T.get("activity_input", "Add Activity"))

    wbs = st.text_input(T.get("wbs", "WBS Code"))
    activity = st.text_input(T.get("activity", "Activity"))
    duration = st.number_input(T.get("duration", "Duration (days)"), min_value=1, max_value=365, value=5)
    dependency = st.text_input(T.get("dependency", "Dependencies (comma-separated)"))

    if st.button(T.get("add_activity", "Add Activity")) and wbs and activity:
        st.session_state.schedule_data.append({
            "WBS": wbs,
            "Activity": activity,
            "Duration": duration,
            "Dependencies": [d.strip() for d in dependency.split(",") if d.strip()]
        })

    df = pd.DataFrame(st.session_state.schedule_data)

    if not df.empty:
        st.subheader(T.get("schedule_table", "Schedule Table"))
        st.dataframe(df)

        # Export to Excel
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="schedule.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i, row in df.iterrows():
            pdf.cell(200, 10, txt=f"{row['WBS']} | {row['Activity']} | {row['Duration']} days", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="schedule.pdf", mime="application/pdf")

        # Firebase Save
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.schedule_data)
            st.success(T.get("save_success", "Schedule saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.schedule_data = data
                st.success(T.get("load_success", "Schedule loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

schedule_developer = run
