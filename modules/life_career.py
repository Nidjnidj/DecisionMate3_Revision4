import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("life_career_title", "Life & Career Decisions")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("life_career", ""))

    if "life_scores" not in st.session_state:
        st.session_state.life_scores = []

    st.subheader(T.get("life_prompt", "List your options and rate them (1-5)"))

    option = st.text_input(T.get("option_label", "Option Name"))
    happiness = st.slider(T.get("happiness", "Happiness (1-5)"), 1, 5, 3)
    stability = st.slider(T.get("stability", "Stability (1-5)"), 1, 5, 3)
    growth = st.slider(T.get("growth", "Growth Potential (1-5)"), 1, 5, 3)

    if st.button(T.get("add_option_btn", "Add Option")) and option:
        total_score = happiness + stability + growth
        st.session_state.life_scores.append({
            "Option": option,
            "Happiness": happiness,
            "Stability": stability,
            "Growth": growth,
            "Total Score": total_score
        })

    if st.session_state.life_scores:
        df = pd.DataFrame(st.session_state.life_scores)
        st.subheader(T.get("score_table", "Scoring Table"))
        st.dataframe(df)

        top = df.sort_values("Total Score", ascending=False).iloc[0]
        st.success(T.get("recommendation", "Best Choice") + f": {top['Option']} ✨")

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Option']} | Happy: {row['Happiness']} | Stable: {row['Stability']} | Growth: {row['Growth']} | Score: {row['Total Score']}"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="life_career_decision.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.life_scores)
            st.success(T.get("save_success", "Options saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.life_scores = data
                st.success(T.get("load_success", "Options loaded."))
            else:
                st.warning(T.get("load_warning", "No saved options found."))

life_career = run
