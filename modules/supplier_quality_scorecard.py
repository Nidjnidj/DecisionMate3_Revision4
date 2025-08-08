import streamlit as st
import pandas as pd

def run(T):
    st.title("🏢 Supplier Quality Scorecard")

    st.markdown("""
    Evaluate supplier performance based on key criteria:  
    - Delivery  
    - Documentation  
    - Product/Service Quality  
    - Communication  
    Scores are out of 10.
    """)

    if "supplier_scores" not in st.session_state:
        st.session_state.supplier_scores = []

    with st.form("supplier_form"):
        supplier = st.text_input("Supplier Name")
        delivery = st.slider("Delivery Performance (0-10)", 0, 10, 7)
        documentation = st.slider("Documentation Quality (0-10)", 0, 10, 7)
        quality = st.slider("Product/Service Quality (0-10)", 0, 10, 7)
        communication = st.slider("Communication (0-10)", 0, 10, 7)

        submitted = st.form_submit_button("➕ Add Evaluation")

    if submitted and supplier:
        total_score = delivery + documentation + quality + communication
        avg_score = total_score / 4

        st.session_state.supplier_scores.append({
            "Supplier": supplier,
            "Delivery": delivery,
            "Documentation": documentation,
            "Quality": quality,
            "Communication": communication,
            "Avg Score": avg_score
        })

    if st.session_state.supplier_scores:
        st.subheader("📊 Supplier Evaluation Table")
        df = pd.DataFrame(st.session_state.supplier_scores)
        st.dataframe(df, use_container_width=True)

        st.download_button("📥 Download Scorecard", df.to_csv(index=False).encode('utf-8'), "supplier_scorecard.csv")
