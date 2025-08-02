import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("s_curve_title", "S-Curve Generator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("s_curve", ""))

    if "s_curve_data" not in st.session_state:
        st.session_state.s_curve_data = []

    st.subheader(T.get("add_progress", "Add Progress Data"))
    period = st.text_input(T.get("period", "Period (e.g., Week 1, Month 1)"))
    value = st.number_input(T.get("value", "Cumulative Progress Value"), min_value=0.0, value=0.0)

    if st.button(T.get("add_entry", "Add Entry")) and period:
        st.session_state.s_curve_data.append({
            "Period": period.strip(),
            "Cumulative Value": value
        })

    df = pd.DataFrame(st.session_state.s_curve_data)

    if not df.empty:
        df = df.sort_values("Period")
        st.subheader(T.get("s_curve_data_table", "Progress Data Table"))
        st.dataframe(df)

        # Plot S-Curve
        st.subheader(T.get("s_curve_chart", "S-Curve Chart"))
        fig, ax = plt.subplots()
        ax.plot(df["Period"], df["Cumulative Value"], marker='o')
        ax.set_xlabel("Period")
        ax.set_ylabel("Cumulative Value")
        ax.set_title("S-Curve")
        st.pyplot(fig)

        # Excel export
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="s_curve.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # PDF export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in df.iterrows():
            pdf.cell(200, 10, txt=f"{row['Period']}: {row['Cumulative Value']}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="s_curve.pdf", mime="application/pdf")

        # Firebase Save
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.s_curve_data)
            st.success(T.get("save_success", "S-Curve data saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.s_curve_data = data
                st.success(T.get("load_success", "S-Curve data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

s_curve = run
