import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.title("📥 I/O List Generator")
    st.markdown(T.get("descriptions", {}).get("io_list_generator", ""))

    if "io_list" not in st.session_state:
        st.session_state.io_list = []

    st.subheader("➕ Add I/O Entry")

    tag = st.text_input("Instrument Tag")
    description = st.text_input("Description")
    signal_type = st.selectbox("Signal Type", ["AI", "AO", "DI", "DO"])
    location = st.text_input("Location")
    plc_address = st.text_input("PLC Address")

    if st.button("Add I/O") and tag:
        st.session_state.io_list.append({
            "Tag": tag,
            "Description": description,
            "Type": signal_type,
            "Location": location,
            "PLC Address": plc_address
        })

    if st.session_state.io_list:
        df = pd.DataFrame(st.session_state.io_list)
        st.subheader("📋 I/O Table")
        st.dataframe(df)

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="I/O List", ln=True)
        for _, row in df.iterrows():
            pdf.multi_cell(0, 10, txt=(
                f"Tag: {row['Tag']}\n"
                f"Description: {row['Description']}\n"
                f"Type: {row['Type']}\n"
                f"Location: {row['Location']}\n"
                f"PLC Address: {row['PLC Address']}\n"
                "-----------------------------"
            ))

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button("Download PDF", pdf_output, file_name="io_list.pdf", mime="application/pdf")

        if st.button("Save"):
            save_project(st.session_state.username, "I/O List", st.session_state.io_list)
            st.success("✅ I/O list saved.")

        if st.button("Load"):
            data = load_project_data(st.session_state.username, "I/O List")
            if data:
                st.session_state.io_list = data
                st.success("✅ I/O list loaded.")
            else:
                st.warning("⚠️ No saved data found.")

io_list_generator = run
