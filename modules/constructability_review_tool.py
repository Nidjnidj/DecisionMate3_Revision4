import streamlit as st
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "constructability_review_tool"

def constructability_review_tool(T):
    st.subheader("🧱 Constructability Review Tool")

    if "constructability_reviews" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.constructability_reviews = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("constructability_review_form"):
        date = st.date_input("Date", value=datetime.today())
        discipline = st.selectbox("Discipline", ["Civil", "Mechanical", "Electrical", "Instrumentation", "Other"])
        issue = st.text_area("Constructability Issue")
        recommendation = st.text_area("Recommendation")
        impact = st.selectbox("Impact", ["Low", "Medium", "High"])
        status = st.selectbox("Status", ["Open", "In Review", "Resolved"])
        reviewer = st.text_input("Reviewer Name")

        submitted = st.form_submit_button("➕ Add Review")
        if submitted:
            st.session_state.constructability_reviews.append({
                "Date": str(date),
                "Discipline": discipline,
                "Issue": issue,
                "Recommendation": recommendation,
                "Impact": impact,
                "Status": status,
                "Reviewer": reviewer
            })
            st.success("✅ Review added!")

    if st.session_state.constructability_reviews:
        df = pd.DataFrame(st.session_state.constructability_reviews)
        st.dataframe(df, use_container_width=True)

        if st.button("💾 Save Reviews"):
            save_project(st.session_state.username, FIREBASE_KEY, st.session_state.constructability_reviews)
            st.success("✅ Reviews saved to Firestore.")

        if st.button("📥 Download Excel"):
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            st.download_button("📄 Download Excel", buffer.getvalue(), file_name="constructability_reviews.xlsx")

        if st.button("📥 Download PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for _, row in df.iterrows():
                for key, val in row.items():
                    pdf.multi_cell(0, 10, f"{key}: {val}", border=0)
                pdf.ln()
            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button("📄 Download PDF", buffer.getvalue(), file_name="constructability_reviews.pdf")

        if st.button("📤 Load Reviews"):
            data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
            st.session_state.constructability_reviews = data_dict["data"] if data_dict and "data" in data_dict else []
            st.success("✅ Reviews loaded from Firestore.")
