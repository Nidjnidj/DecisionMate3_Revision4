import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import base64
from firebase_db import save_project, load_project_data

def weather_impact_tracker(T):
    st.header("🌦️ Weather Impact Tracker")

    if "weather_impact_data" not in st.session_state:
        st.session_state.weather_impact_data = []

    with st.form("weather_impact_form", clear_on_submit=True):
        date = st.date_input("Date")
        weather_condition = st.text_input("Weather Condition")
        impact = st.selectbox("Impact", ["None", "Minor", "Moderate", "Severe"])
        description = st.text_area("Description of Impact")
        actions_taken = st.text_area("Actions Taken")
        responsible = st.text_input("Responsible Person")

        submitted = st.form_submit_button("➕ Add Record")
        if submitted:
            st.session_state.weather_impact_data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Weather Condition": weather_condition,
                "Impact": impact,
                "Description": description,
                "Actions Taken": actions_taken,
                "Responsible": responsible
            })
            st.success("Record added.")

    if st.session_state.weather_impact_data:
        df = pd.DataFrame(st.session_state.weather_impact_data)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button(T["save"]):
                save_project(st.session_state.username, "weather_impact_tracker", st.session_state.weather_impact_data)
                st.success(T["save_success"])

        with col2:
            if st.button(T["load"]):
                loaded = load_project_data(st.session_state.username, "weather_impact_tracker")
                if loaded:
                    st.session_state.weather_impact_data = loaded["data"]
                    st.success(T["load_success"])
                else:
                    st.warning(T["load_warning"])

        def convert_df_to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='WeatherImpact')
            output.seek(0)
            return output

        st.download_button(
            label="⬇️ Download Excel",
            data=convert_df_to_excel(df),
            file_name="weather_impact_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        def generate_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Weather Impact Report", ln=1, align="C")
            for record in data:
                for k, v in record.items():
                    pdf.cell(200, 10, txt=f"{k}: {v}", ln=1)
                pdf.cell(200, 5, txt="--------------------------", ln=1)
            return pdf.output(dest='S').encode('latin1')

        pdf_data = generate_pdf(st.session_state.weather_impact_data)
        b64 = base64.b64encode(pdf_data).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="weather_impact_log.pdf">📄 Download PDF</a>', unsafe_allow_html=True)
