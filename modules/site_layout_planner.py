import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import base64
from firebase_db import save_project, load_project_data

def site_layout_planner(T):
    st.header("📍 Site Layout Planner")

    if "site_layout_data" not in st.session_state:
        st.session_state.site_layout_data = []

    with st.form("site_layout_form", clear_on_submit=True):
        date = st.date_input("Date")
        zone_name = st.text_input("Zone Name")
        zone_type = st.selectbox("Zone Type", ["Storage", "Work Area", "Safety", "Admin", "Other"])
        coordinates = st.text_input("Coordinates")
        notes = st.text_area("Notes")
        assigned_to = st.text_input("Assigned To")

        submitted = st.form_submit_button("➕ Add Zone")
        if submitted:
            st.session_state.site_layout_data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Zone Name": zone_name,
                "Zone Type": zone_type,
                "Coordinates": coordinates,
                "Notes": notes,
                "Assigned To": assigned_to
            })
            st.success("Zone added.")

    if st.session_state.site_layout_data:
        df = pd.DataFrame(st.session_state.site_layout_data)
        st.dataframe(df, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            if st.button(T["save"]):
                save_project(st.session_state.username, "site_layout_planner", st.session_state.site_layout_data)
                st.success(T["save_success"])

        with col2:
            if st.button(T["load"]):
                loaded = load_project_data(st.session_state.username, "site_layout_planner")
                if loaded:
                    st.session_state.site_layout_data = loaded["data"]
                    st.success(T["load_success"])
                else:
                    st.warning(T["load_warning"])

        def convert_df_to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Layout')
            output.seek(0)
            return output

        st.download_button(
            label="⬇️ Download Excel",
            data=convert_df_to_excel(df),
            file_name="site_layout.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        def generate_pdf(data):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Site Layout Planner Report", ln=1, align="C")
            for record in data:
                for k, v in record.items():
                    pdf.cell(200, 10, txt=f"{k}: {v}", ln=1)
                pdf.cell(200, 5, txt="--------------------------", ln=1)
            return pdf.output(dest='S').encode('latin1')

        pdf_data = generate_pdf(st.session_state.site_layout_data)
        b64 = base64.b64encode(pdf_data).decode()
        st.markdown(f'<a href="data:application/octet-stream;base64,{b64}" download="site_layout.pdf">📄 Download PDF</a>', unsafe_allow_html=True)
