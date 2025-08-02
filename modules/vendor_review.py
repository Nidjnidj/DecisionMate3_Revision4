import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("vendor_review_title", "Vendor Performance Review")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("vendor_review", ""))

    if "vendor_reviews" not in st.session_state:
        st.session_state.vendor_reviews = []

    st.subheader(T.get("add_review", "Add Vendor Review"))
    vendor = st.text_input(T.get("vendor_name", "Vendor Name"))
    criteria = st.text_input(T.get("review_criteria", "Performance Criteria"))
    rating = st.slider(T.get("rating", "Rating (1-10)"), 1, 10)
    comments = st.text_area(T.get("comments", "Comments"))

    if st.button(T.get("add_button", "Add Review")) and vendor and criteria:
        st.session_state.vendor_reviews.append({
            "Vendor": vendor,
            "Criteria": criteria,
            "Rating": rating,
            "Comments": comments
        })

    if st.session_state.vendor_reviews:
        df = pd.DataFrame(st.session_state.vendor_reviews)
        st.subheader(T.get("review_log", "Review Log"))
        st.dataframe(df)

        # Summary Table
        avg_df = df.groupby("Vendor")["Rating"].mean().reset_index()
        avg_df.columns = ["Vendor", "Average Rating"]
        st.subheader(T.get("average_rating", "Average Ratings"))
        st.dataframe(avg_df.sort_values("Average Rating", ascending=False))

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Vendor: {row['Vendor']}\n"
                f"Criteria: {row['Criteria']}\n"
                f"Rating: {row['Rating']}\n"
                f"Comments: {row['Comments']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="vendor_review_log.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.vendor_reviews)
            st.success(T.get("save_success", "Reviews saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.vendor_reviews = data
                st.success(T.get("load_success", "Reviews loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

vendor_review = run
