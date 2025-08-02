import streamlit as st
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("contracts_development_title", "Contracts Development")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("contracts_development", ""))

    templates = {
        "Construction": [
            "Scope of Work", "Payment Terms", "Change Orders", "Dispute Resolution"
        ],
        "Procurement": [
            "Delivery Terms", "Payment Milestones", "Quality Standards", "Inspection Rights"
        ],
        "Logistics": [
            "Cargo Handling", "Delivery Schedule", "Insurance", "Liability"
        ],
        "Custom": []
    }

    contract_type = st.selectbox(T.get("select_contract_type", "Select Contract Type"), list(templates.keys()))
    contract_title = st.text_input(T.get("contract_title", "Contract Title"))
    party_a = st.text_input(T.get("party_a", "Party A"))
    party_b = st.text_input(T.get("party_b", "Party B"))

    st.subheader(T.get("clauses", "Clauses"))
    selected_clauses = []
    if contract_type != "Custom":
        selected_clauses = st.multiselect(T.get("select_clauses", "Select Clauses"), templates[contract_type])
    else:
        custom_clause = st.text_area(T.get("custom_clause", "Enter your custom clause"))
        if custom_clause:
            selected_clauses.append(custom_clause)

    if st.button(T.get("generate", "Generate Contract")) and contract_title and party_a and party_b:
        content = f"{contract_title}\n\nBetween: {party_a}\nAnd: {party_b}\n\nClauses:\n"
        for clause in selected_clauses:
            content += f"\n- {clause}"

        st.text_area(T.get("preview", "Preview Contract"), value=content, height=300)

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for line in content.split("\n"):
            pdf.multi_cell(0, 10, txt=line)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="contract.pdf", mime="application/pdf")

        # === Save to Firebase ===
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, {
                "title": contract_title,
                "party_a": party_a,
                "party_b": party_b,
                "clauses": selected_clauses
            })
            st.success(T.get("save_success", "Contract saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.contract_title = data.get("title", "")
                st.session_state.party_a = data.get("party_a", "")
                st.session_state.party_b = data.get("party_b", "")
                st.session_state.clauses = data.get("clauses", [])
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

contracts_development = run
