import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("what_if_title", "What-If Scenario Simulator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("what_if", ""))

    if "scenarios" not in st.session_state:
        st.session_state.scenarios = []

    st.subheader(T.get("add_scenario", "Add New Scenario"))

    scenario_name = st.text_input(T.get("scenario_name", "Scenario Name"))
    variable1 = st.number_input(T.get("variable1", "Variable 1 (e.g., Sales)"), value=1000.0)
    variable2 = st.number_input(T.get("variable2", "Variable 2 (e.g., Cost)"), value=500.0)
    variable3 = st.number_input(T.get("variable3", "Variable 3 (e.g., Conversion Rate)"), value=0.1)

    if st.button(T.get("add_scenario_btn", "Add Scenario")) and scenario_name:
        result = variable1 * variable3 - variable2
        st.session_state.scenarios.append({
            "Scenario": scenario_name,
            "Variable 1": variable1,
            "Variable 2": variable2,
            "Variable 3": variable3,
            "Result": result
        })

    if st.session_state.scenarios:
        df = pd.DataFrame(st.session_state.scenarios)
        st.subheader(T.get("scenario_results", "Scenario Results"))
        st.dataframe(df)

        best = df.loc[df["Result"].idxmax()]
        st.success(f"🏆 {T.get('best_scenario', 'Best Scenario')}: {best['Scenario']} | {T.get('result', 'Result')}: {best['Result']:.2f}")

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            line = f"{row['Scenario']} -> Result: {row['Result']:.2f}"
            pdf.cell(200, 10, txt=line, ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="what_if_scenarios.pdf", mime="application/pdf")

        # Save/Load from Firebase
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.scenarios)
            st.success(T.get("save_success", "Scenarios saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.scenarios = data
                st.success(T.get("load_success", "Scenarios loaded."))
            else:
                st.warning(T.get("load_warning", "No saved scenarios found."))

what_if = run
