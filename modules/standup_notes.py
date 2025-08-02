import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from datetime import date
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("standup_notes_title", "Daily Stand-up Notes")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("standup_notes", ""))

    st.subheader(T.get("add_update", "Add Today's Update"))

    name = st.text_input(T.get("name", "Team Member"))
    yesterday = st.text_area(T.get("yesterday", "What did you do yesterday?"))
    today = st.text_area(T.get("today", "What will you do today?"))
    blockers = st.text_area(T.get("blockers", "Any blockers or issues?"))
    current_date = date.today().strftime("%Y-%m-%d")

    if "standup_log" not in st.session_state:
        st.session_state.standup_log = []

    if st.button(T.get("submit_update", "Submit Update")) and name:
        st.session_state.standup_log.append({
            "Date": current_date,
            "Name": name,
            "Yesterday": yesterday,
            "Today": today,
            "Blockers": blockers
        })

    df = pd.DataFrame(st.session_state.standup_log)

    if not df.empty:
        st.subheader(T.get("standup_log", "Team Stand-up Log"))
        st.dataframe(df)

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="standup_log.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            row = df.iloc[i]
            pdf.multi_cell(0, 10, txt=f"{row['Date']} - {row['Name']}\nYesterday: {row['Yesterday']}\nToday: {row['Today']}\nBlockers: {row['Blockers']}\n", border=1)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="standup_notes.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, df.to_dict())
            st.success(T.get("save_success", "Stand-up log saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                df_loaded = pd.DataFrame(data)
                st.session_state.standup_log = df_loaded.to_dict(orient="records")
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

standup_notes = run
