import streamlit as st
import pandas as pd
import numpy as np
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("contract_analyzer_title", "Contract Decision Analyzer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("contract_analyzer", ""))

    st.subheader(T.get("input_section", "Input Contract Options and Criteria"))

    num_contracts = st.number_input(T.get("num_contracts", "Number of Contracts"), min_value=2, max_value=10, value=3, step=1)
    num_criteria = st.number_input(T.get("num_criteria", "Number of Criteria"), min_value=1, max_value=10, value=3, step=1)

    contract_names = [st.text_input(f"{T.get('contract_name', 'Contract Name')} {i+1}", key=f"contract_{i}") for i in range(num_contracts)]
    criteria_names = [st.text_input(f"{T.get('criteria_name', 'Criteria')} {j+1}", key=f"criteria_{j}") for j in range(num_criteria)]

    # Use enumerate to make keys unique
    weights = [st.slider(f"{T.get('weight_for', 'Weight for')} {c}", 0, 100, 20, key=f"weight_{i}_{c}") for i, c in enumerate(criteria_names)]
    total_weight = sum(weights)
    weights = [w / total_weight if total_weight > 0 else 0 for w in weights]

    if st.button(T.get("evaluate", "Evaluate Contracts")) and all(contract_names) and all(criteria_names):
        scores = []
        for i, c_name in enumerate(contract_names):
            st.markdown(f"**{c_name}**")
            contract_scores = [st.number_input(f"{c_name} - {crit}", min_value=0.0, max_value=10.0, step=0.1, key=f"score_{i}_{j}") for j, crit in enumerate(criteria_names)]
            weighted_score = np.dot(contract_scores, weights)
            scores.append((c_name, weighted_score))

        df = pd.DataFrame(scores, columns=["Contract", "Weighted Score"])
        df = df.sort_values("Weighted Score", ascending=False).reset_index(drop=True)

        st.success(T.get("results", "Evaluation Results:"))
        st.dataframe(df)

        # Export to Excel
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="contract_evaluation.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            pdf.cell(200, 10, txt=f"{df.iloc[i, 0]}: {round(df.iloc[i, 1], 2)}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="contract_evaluation.pdf", mime="application/pdf")

        # Save to Firebase
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, df.to_dict(orient="records"))
            st.success(T.get("save_success", "Evaluation saved."))

    # Load should always be available
    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, title)
        if data:
            df_loaded = pd.DataFrame(data)
            st.dataframe(df_loaded)
            st.success(T.get("load_success", "Data loaded."))
        else:
            st.warning(T.get("load_warning", "No saved data found."))

contract_analyzer = run
