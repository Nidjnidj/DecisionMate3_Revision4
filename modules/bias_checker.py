import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("bias_checker_title", "Cognitive Bias Checker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("bias_checker", ""))

    if "bias_checks" not in st.session_state:
        st.session_state.bias_checks = []

    st.subheader(T.get("add_check", "Add Decision to Evaluate"))

    decision = st.text_input(T.get("decision_prompt", "Describe your decision"))
    bias_type = st.selectbox(T.get("select_bias", "Select Potential Bias"), [
        "Confirmation Bias", "Anchoring Bias", "Loss Aversion", "Status Quo Bias",
        "Overconfidence", "Availability Heuristic", "Framing Effect"
    ])
    mitigated = st.selectbox(T.get("mitigation", "Have you mitigated this bias?"), ["Yes", "No"])

    if st.button(T.get("add_check_btn", "Add Bias Evaluation")) and decision:
        st.session_state.bias_checks.append({
            "Decision": decision,
            "Bias Type": bias_type,
            "Mitigated": mitigated
        })

    if st.session_state.bias_checks:
        df = pd.DataFrame(st.session_state.bias_checks)
        st.subheader(T.get("bias_list", "Evaluated Decisions"))
        st.dataframe(df)

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Decision']} | Bias: {row['Bias Type']} | Mitigated: {row['Mitigated']}"
            pdf.cell(200, 10, txt=line, ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="bias_checker.pdf", mime="application/pdf")

        # Firebase Save/Load
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.bias_checks)
            st.success(T.get("save_success", "Decisions saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.bias_checks = data
                st.success(T.get("load_success", "Decisions loaded."))
            else:
                st.warning(T.get("load_warning", "No saved decisions found."))

bias_checker = run
