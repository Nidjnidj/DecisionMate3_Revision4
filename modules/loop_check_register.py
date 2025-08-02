import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.title("📋 Loop Check Register")
    st.markdown(T.get("descriptions", {}).get("loop_check_register", ""))

    if "loop_checks" not in st.session_state:
        st.session_state.loop_checks = []

    st.subheader("➕ Add New Loop Check")
    loop_id = st.text_input("Loop ID")
    instrument_tag = st.text_input("Instrument Tag")
    status = st.selectbox("Status", ["Pending", "Completed", "Failed"])
    remarks = st.text_area("Remarks")

    if st.button("Add Entry") and loop_id and instrument_tag:
        st.session_state.loop_checks.append({
            "Loop ID": loop_id,
            "Instrument Tag": instrument_tag,
            "Status": status,
            "Remarks": remarks
        })

    if st.session_state.loop_checks:
        df = pd.DataFrame(st.session_state.loop_checks)
        st.subheader("✅ Loop Check Register")
        st.dataframe(df)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Loop Check Register", ln=True)
        for _, row in df.iterrows():
            line = f"Loop ID: {row['Loop ID']} | Tag: {row['Instrument Tag']} | Status: {row['Status']} | Remarks: {row['Remarks']}"
            pdf.multi_cell(0, 10, line)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button("Download PDF", pdf_output, file_name="loop_check_register.pdf", mime="application/pdf")

        if st.button("Save"):
            save_project(st.session_state.username, "Loop Check Register", st.session_state.loop_checks)
            st.success("✅ Loop checks saved.")

        if st.button("Load"):
            data = load_project_data(st.session_state.username, "Loop Check Register")
            if data:
                st.session_state.loop_checks = data
                st.success("✅ Loaded saved loop checks.")
            else:
                st.warning("⚠️ No saved data found.")

loop_check_register = run
