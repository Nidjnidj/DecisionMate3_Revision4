import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("retro_board_title", "Retrospective Board")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("retrospective_board", ""))

    st.subheader(T.get("add_feedback", "Add Feedback"))

    name = st.text_input(T.get("name", "Team Member"))
    good = st.text_area(T.get("what_went_well", "What went well?"))
    bad = st.text_area(T.get("what_didnt_go_well", "What didn't go well?"))
    ideas = st.text_area(T.get("suggestions", "Suggestions for improvement"))

    if "retro_log" not in st.session_state:
        st.session_state.retro_log = []

    if st.button(T.get("submit_feedback", "Submit Feedback")) and name:
        st.session_state.retro_log.append({
            "Name": name,
            "What Went Well": good,
            "What Didn't Go Well": bad,
            "Suggestions": ideas
        })

    df = pd.DataFrame(st.session_state.retro_log)

    if not df.empty:
        st.subheader(T.get("retro_log", "Team Retrospective Log"))
        st.dataframe(df)

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="retrospective_log.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            row = df.iloc[i]
            pdf.multi_cell(0, 10, txt=f"{row['Name']}\n✅ {row['What Went Well']}\n❌ {row['What Didn\'t Go Well']}\n💡 {row['Suggestions']}\n", border=1)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="retrospective_log.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, df.to_dict())
            st.success(T.get("save_success", "Retrospective saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                df_loaded = pd.DataFrame(data)
                st.session_state.retro_log = df_loaded.to_dict(orient="records")
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

retrospective_board = run
