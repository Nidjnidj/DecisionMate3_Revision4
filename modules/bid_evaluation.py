import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("bid_eval_title", "Bid Evaluation Matrix")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("bid_evaluation", ""))

    if "bid_matrix" not in st.session_state:
        st.session_state.bid_matrix = []

    st.subheader(T.get("add_criteria", "Add Bid Scoring Criteria"))
    bidder = st.text_input(T.get("bidder_name", "Bidder Name"))
    criteria = st.text_input(T.get("criteria", "Criteria"))
    score = st.number_input(T.get("score", "Score"), 0, 100)

    if st.button(T.get("add_button", "Add to Matrix")) and bidder and criteria:
        st.session_state.bid_matrix.append({
            "Bidder": bidder,
            "Criteria": criteria,
            "Score": score
        })

    if st.session_state.bid_matrix:
        df = pd.DataFrame(st.session_state.bid_matrix)
        st.subheader(T.get("evaluation_table", "Evaluation Matrix"))
        st.dataframe(df)

        total_df = df.groupby("Bidder")["Score"].sum().reset_index()
        total_df.columns = ["Bidder", "Total Score"]
        st.subheader(T.get("total_score", "Total Scores"))
        st.dataframe(total_df.sort_values("Total Score", ascending=False))

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=f"{row['Bidder']} | {row['Criteria']} | Score: {row['Score']}", ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="bid_evaluation_matrix.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.bid_matrix)
            st.success(T.get("save_success", "Bid matrix saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.bid_matrix = data
                st.success(T.get("load_success", "Bid matrix loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

bid_evaluation = run
