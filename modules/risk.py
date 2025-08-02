import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("risk_title", "General Risk Analyzer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("risk", ""))

    if "risk_entries" not in st.session_state:
        st.session_state.risk_entries = []

    st.subheader(T.get("add_risk", "Add New Risk"))

    risk_name = st.text_input(T.get("risk_name", "Risk Description"))
    probability = st.slider(T.get("probability", "Probability (1-5)"), 1, 5, 3)
    impact = st.slider(T.get("impact", "Impact (1-5)"), 1, 5, 3)

    if st.button(T.get("add_risk_btn", "Add Risk")) and risk_name:
        score = probability * impact
        if score <= 6:
            level = "Low"
        elif score <= 12:
            level = "Medium"
        else:
            level = "High"

        st.session_state.risk_entries.append({
            "Risk": risk_name,
            "Probability": probability,
            "Impact": impact,
            "Score": score,
            "Level": level
        })

    if st.session_state.risk_entries:
        df = pd.DataFrame(st.session_state.risk_entries)
        st.subheader(T.get("risk_table", "Risk Table"))
        st.dataframe(df)

        st.markdown("### ⚠️ " + T.get("risk_summary", "Summary by Risk Level"))
        st.write(df["Level"].value_counts())

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Risk']} | Prob: {row['Probability']} | Impact: {row['Impact']} | Score: {row['Score']} | Level: {row['Level']}"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="risk_analysis.pdf", mime="application/pdf")

        # Save to Firebase
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.risk_entries)
            st.success(T.get("save_success", "Risks saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.risk_entries = data
                st.success(T.get("load_success", "Risks loaded."))
            else:
                st.warning(T.get("load_warning", "No saved risks found."))

risk = run
