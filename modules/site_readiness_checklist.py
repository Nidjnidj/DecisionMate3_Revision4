# modules/site_readiness_checklist.py

import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T.get("site_readiness_checklist_title", "Site Readiness Checklist"))
    st.markdown(T.get("descriptions", {}).get("site_readiness_checklist", "Ensure the construction site is ready before project start."))

    checklist_items = [
        "Site Survey Completed",
        "Permits Obtained",
        "Utility Access Confirmed",
        "Access Roads Prepared",
        "Site Cleared of Debris",
        "Fencing Installed",
        "Temporary Facilities Setup",
        "Safety Signage Posted"
    ]

    st.subheader(T.get("checklist", "Checklist"))
    status = {}
    for item in checklist_items:
        status[item] = st.checkbox(item)

    if st.button(T.get("generate_report", "Generate Report")):
        checked_df = pd.DataFrame({
            "Item": checklist_items,
            "Completed": ["✅" if status[i] else "❌" for i in checklist_items]
        })
        st.dataframe(checked_df)

        # PDF export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=T.get("site_readiness_checklist_title", "Site Readiness Checklist"), ln=True)
        for i in checklist_items:
            mark = "✅" if status[i] else "❌"
            pdf.cell(200, 10, txt=f"{mark} {i}", ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"),
                           data=pdf_output,
                           file_name="site_readiness_checklist.pdf",
                           mime="application/pdf")

        # Firebase save
        save_project(st.session_state.username, "Site Readiness", status)
        st.success(T.get("save_success", "Checklist saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, "Site Readiness")
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

site_readiness_checklist = run
