import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("interface_review_title", "Interface Review Summary")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("interface_review", ""))

    if "interface_reviews" not in st.session_state:
        st.session_state.interface_reviews = []

    st.subheader(T.get("add_review", "Add Review Summary"))
    review_id = st.text_input(T.get("review_id", "Review ID"))
    date = st.date_input(T.get("review_date", "Review Date"))
    involved_disciplines = st.text_input(T.get("involved_disciplines", "Involved Disciplines"))
    topics_discussed = st.text_area(T.get("topics_discussed", "Topics Discussed"))
    action_items = st.text_area(T.get("action_items", "Action Items"))

    if st.button(T.get("add_button", "Add Review")) and review_id:
        st.session_state.interface_reviews.append({
            "Review ID": review_id,
            "Date": str(date),
            "Disciplines": involved_disciplines,
            "Topics Discussed": topics_discussed,
            "Action Items": action_items
        })

    if st.session_state.interface_reviews:
        df = pd.DataFrame(st.session_state.interface_reviews)
        st.subheader(T.get("review_table", "Review Summary Table"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Review ID: {row['Review ID']}\n"
                f"Date: {row['Date']}\n"
                f"Disciplines: {row['Disciplines']}\n"
                f"Topics Discussed: {row['Topics Discussed']}\n"
                f"Action Items: {row['Action Items']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="interface_review_summary.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.interface_reviews)
            st.success(T.get("save_success", "Review summary saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.interface_reviews = data
                st.success(T.get("load_success", "Review summary loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

interface_review = run
