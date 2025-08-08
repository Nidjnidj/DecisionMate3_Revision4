import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import base64
from firebase_db import save_project, load_project_data

def equipment_usage_log(T):
    st.header("🏗️ Equipment Usage Log")

    if "equipment_usage_data" not in st.session_state:
        st.session_state.equipment_usage_data = []

    with st.form("equipment_usage_form", clear_on_submit=True):
        date = st.date_input("Date")
        equipment = st.text_input("Equipment Name/ID")
        usage_hours = st.number_input("Usage Hours", min_value=0.0, step=0.1)
        operator = st.text_input("Operator")
        purpose = st.text_area("Purpose/Task")
        remarks = st.text_area("Remarks")

        submitted = st.form_submit_button("➕ Add Record")
        if submitted:
            st.session_state.equipment_usage_data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Equipment": equipment,
                "Usage Hours": usage_hours,
                "Operator": operator,
                "Purpose": purpose,
                "Remarks": remarks
            })
            st.success("Record added.")

    if st.session_state.equipment_usage_data:
        df = pd.DataFrame(st.session_state.equipment_usage_data)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button(T["save"]):
                save_project(st.session_state.username, "equipment_usage_log", st.session_state.equipment_usage_data)
                st.success(T["save_success"])

        with col2:
            if st.button(T["load"]):
                loaded = load_project_data(st.session_state.username, "equipment_usage_log")
                if loaded:
                    st.session_state.equipment_usage_data = loaded["data"]
                    st.success(T["load_success"])
                else:
                    st.warning(T["load_warning"])

        def convert_df_to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='EquipmentUsage')
            output.seek(0)
            return output

        st.download_button(
            label="⬇️ Download Excel",
            data=convert_df_to_excel(df),
            file_name="equipment_usage_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        def generate_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Equipment Usage Report", ln=1, align="C")
            for record in data:
                for k, v in record.items():
                    pdf.cell(200, 10, txt=f"{k}: {v}", ln=1)
                pdf.cell(200, 5, txt="--------------------------", ln=1)
            return pdf.output(dest='S').encode('latin1')

        pdf_data = generate_pdf(st.session_state.equipment_usage_data)
        b64 = base64.b64encode(pdf_data).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="equipment_usage_log.pdf">📄 Download PDF</a>', unsafe_allow_html=True)
