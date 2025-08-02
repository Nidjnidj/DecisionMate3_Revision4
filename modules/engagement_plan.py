import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("engagement_plan_title", "Engagement Plan Builder")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("engagement_plan", ""))

    if "engagement_plans" not in st.session_state:
        st.session_state.engagement_plans = []

    st.subheader(T.get("add_plan", "Add Engagement Plan"))
    stakeholder = st.text_input(T.get("stakeholder_name", "Stakeholder Name"))
    interest = st.selectbox(T.get("interest_level", "Interest Level"), ["High", "Medium", "Low"])
    influence = st.selectbox(T.get("influence_level", "Influence Level"), ["High", "Medium", "Low"])
    communication_method = st.text_input(T.get("communication_method", "Communication Method"))
    frequency = st.text_input(T.get("communication_frequency", "Frequency"))

    if st.button(T.get("add_button", "Add Plan")) and stakeholder:
        st.session_state.engagement_plans.append({
            "Stakeholder": stakeholder,
            "Interest": interest,
            "Influence": influence,
            "Method": communication_method,
            "Frequency": frequency
        })

    if st.session_state.engagement_plans:
        df = pd.DataFrame(st.session_state.engagement_plans)
        st.subheader(T.get("engagement_table", "Engagement Plan Table"))
        st.dataframe(df)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Stakeholder: {row['Stakeholder']}\n"
                f"Interest: {row['Interest']}\n"
                f"Influence: {row['Influence']}\n"
                f"Method: {row['Method']}\n"
                f"Frequency: {row['Frequency']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="engagement_plan.pdf", mime="application/pdf")

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.engagement_plans)
            st.success(T.get("save_success", "Plan saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.engagement_plans = data
                st.success(T.get("load_success", "Plan loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

engagement_plan = run
