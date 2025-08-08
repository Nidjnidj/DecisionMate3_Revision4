import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import base64
from firebase_db import save_project, load_project_data

def construction_risk_log(T):
    st.header("🧯 Construction Risk Log")

    if "construction_risk_data" not in st.session_state:
        st.session_state.construction_risk_data = []

    with st.form("construction_risk_form", clear_on_submit=True):
        description = st.text_input("Risk Description")
        area = st.text_input("Area")
        category = st.selectbox("Category", ["Safety", "Schedule", "Quality", "Cost", "Other"])
        likelihood = st.selectbox("Likelihood", ["Low", "Medium", "High"])
        impact = st.selectbox("Impact", ["Low", "Medium", "High"])
        mitigation = st.text_area("Mitigation Plan")
        owner = st.text_input("Risk Owner")
        status = st.selectbox("Status", ["Open", "In Progress", "Closed"])

        submitted = st.form_submit_button("➕ Add Risk")
        if submitted:
            st.session_state.construction_risk_data.append({
                "Description": description,
                "Area": area,
                "Category": category,
                "Likelihood": likelihood,
                "Impact": impact,
                "Mitigation Plan": mitigation,
                "Owner": owner,
                "Status": status
            })
            st.success("Risk added.")

    if st.session_state.construction_risk_data:
        df = pd.DataFrame(st.session_state.construction_risk_data)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button(T["save"]):
                save_project(st.session_state.username, "construction_risk_log", st.session_state.construction_risk_data)
                st.success(T["save_success"])

        with col2:
            if st.button(T["load"]):
                loaded = load_project_data(st.session_state.username, "construction_risk_log")
                if loaded:
                    st.session_state.construction_risk_data = loaded["data"]
                    st.success(T["load_success"])
                else:
                    st.warning(T["load_warning"])

        def convert_df_to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='RiskLog')
            output.seek(0)
            return output

        st.download_button(
            label="⬇️ Download Excel",
            data=convert_df_to_excel(df),
            file_name="construction_risk_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        def generate_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Construction Risk Log Report", ln=1, align="C")
            for record in data:
                for k, v in record.items():
                    pdf.cell(200, 10, txt=f"{k}: {v}", ln=1)
                pdf.cell(200, 5, txt="--------------------------", ln=1)
            return pdf.output(dest='S').encode('latin1')

        pdf_data = generate_pdf(st.session_state.construction_risk_data)
        b64 = base64.b64encode(pdf_data).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="construction_risk_log.pdf">📄 Download PDF</a>', unsafe_allow_html=True)
