import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("knowledge_linker_title", "Knowledge Base Linker")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("knowledge_linker", ""))

    st.subheader(T.get("link_knowledge", "Link Decision to Knowledge/Source"))

    term = st.text_input(T.get("decision_term", "Term / Topic / Decision"))
    source = st.text_input(T.get("source_link", "Source / Documentation / Link"))
    notes = st.text_area(T.get("notes", "Notes / Justification"))

    if "knowledge_table" not in st.session_state:
        st.session_state.knowledge_table = []

    if st.button(T.get("add_entry", "Add Entry")) and term:
        st.session_state.knowledge_table.append({
            "Term / Decision": term,
            "Source": source,
            "Notes": notes
        })

    df = pd.DataFrame(st.session_state.knowledge_table)

    if not df.empty:
        st.subheader(T.get("linked_entries", "Linked Knowledge Table"))
        st.dataframe(df)

        # === Excel Export ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="knowledge_links.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for i in range(len(df)):
            row = df.iloc[i]
            pdf.cell(200, 10, txt=f"{row['Term / Decision']}: {row['Source']} | {row['Notes']}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="knowledge_links.pdf", mime="application/pdf")

        # === Firebase Save ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, df.to_dict())
            st.success(T.get("save_success", "Project saved successfully."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                df_loaded = pd.DataFrame(data)
                st.session_state.knowledge_table = df_loaded.to_dict(orient="records")
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

knowledge_linker = run
