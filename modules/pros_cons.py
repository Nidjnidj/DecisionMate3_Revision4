import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("pros_cons_title", "Pros and Cons Analyzer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("pros_cons", ""))

    if "pros_list" not in st.session_state:
        st.session_state.pros_list = []
    if "cons_list" not in st.session_state:
        st.session_state.cons_list = []

    st.subheader(T.get("add_pros", "Add Pros"))
    pro_desc = st.text_input(T.get("pro_description", "Pro Description"))
    pro_weight = st.slider(T.get("pro_weight", "Pro Weight"), 1, 10, 5)
    if st.button(T.get("add_pro", "Add Pro")):
        st.session_state.pros_list.append({"Description": pro_desc, "Weight": pro_weight})

    st.subheader(T.get("add_cons", "Add Cons"))
    con_desc = st.text_input(T.get("con_description", "Con Description"))
    con_weight = st.slider(T.get("con_weight", "Con Weight"), 1, 10, 5)
    if st.button(T.get("add_con", "Add Con")):
        st.session_state.cons_list.append({"Description": con_desc, "Weight": con_weight})

    pros_df = pd.DataFrame(st.session_state.pros_list)
    cons_df = pd.DataFrame(st.session_state.cons_list)

    if not pros_df.empty or not cons_df.empty:
        st.subheader(T.get("results", "Decision Summary"))

        if not pros_df.empty:
            st.markdown("### 👍 " + T.get("pros", "Pros"))
            st.dataframe(pros_df)
        if not cons_df.empty:
            st.markdown("### 👎 " + T.get("cons", "Cons"))
            st.dataframe(cons_df)

        pro_score = pros_df["Weight"].sum() if not pros_df.empty else 0
        con_score = cons_df["Weight"].sum() if not cons_df.empty else 0
        net_score = pro_score - con_score

        st.markdown(f"✅ **{T.get('total_pro_score', 'Total Pro Score')}:** {pro_score}")
        st.markdown(f"❌ **{T.get('total_con_score', 'Total Con Score')}:** {con_score}")
        st.markdown(f"🧠 **{T.get('net_score', 'Net Score')}:** {net_score}")

        if net_score > 0:
            st.success(T.get("decision_positive", "Overall positive decision."))
        elif net_score < 0:
            st.error(T.get("decision_negative", "Overall negative decision."))
        else:
            st.warning(T.get("decision_neutral", "Neutral outcome."))

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        pdf.cell(200, 10, txt=f"Total Pro Score: {pro_score}", ln=True)
        pdf.cell(200, 10, txt=f"Total Con Score: {con_score}", ln=True)
        pdf.cell(200, 10, txt=f"Net Score: {net_score}", ln=True)

        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="pros_cons_analysis.pdf", mime="application/pdf")

        # Save to Firebase
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, {
                "pros": st.session_state.pros_list,
                "cons": st.session_state.cons_list
            })
            st.success(T.get("save_success", "Data saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.pros_list = data.get("pros", [])
                st.session_state.cons_list = data.get("cons", [])
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

pros_cons = run
