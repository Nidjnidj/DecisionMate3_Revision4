import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data
from datetime import date

def run(T):
    title = T.get("delivery_tracker_title", "Delivery Milestone Tracker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("delivery_tracker", ""))

    if "milestone_tracker" not in st.session_state:
        st.session_state.milestone_tracker = []

    st.subheader(T.get("add_milestone", "Add Delivery Milestone"))
    supplier = st.text_input(T.get("supplier_name", "Supplier Name"))
    item = st.text_input(T.get("item_name", "Item or Equipment"))
    milestone = st.text_input(T.get("milestone", "Milestone Description"))
    due_date = st.date_input(T.get("due_date", "Due Date"), value=date.today())
    status = st.selectbox(T.get("status", "Status"), ["Not Started", "In Progress", "Completed", "Delayed"])

    if st.button(T.get("add_button", "Add Milestone")) and supplier and item and milestone:
        st.session_state.milestone_tracker.append({
            "Supplier": supplier,
            "Item": item,
            "Milestone": milestone,
            "Due Date": due_date.strftime("%Y-%m-%d"),
            "Status": status
        })

    if st.session_state.milestone_tracker:
        df = pd.DataFrame(st.session_state.milestone_tracker)
        st.subheader(T.get("milestone_log", "Milestone Log"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=f"{row['Supplier']} | {row['Item']} | {row['Milestone']} | {row['Due Date']} | {row['Status']}", ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="delivery_milestone_tracker.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.milestone_tracker)
            st.success(T.get("save_success", "Milestones saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.milestone_tracker = data
                st.success(T.get("load_success", "Milestones loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

delivery_tracker = run
