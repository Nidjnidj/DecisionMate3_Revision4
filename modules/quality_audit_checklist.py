import streamlit as st
import pandas as pd

def run(T):
    st.title("🧾 Quality Audit Checklist")

    st.markdown("""
    Use this checklist during quality audits.  
    Mark compliance for each item and note findings.
    """)

    if "audit_items" not in st.session_state:
        st.session_state.audit_items = []

    with st.form("audit_form"):
        item = st.text_input("Audit Item")
        result = st.selectbox("Compliance Status", ["Compliant", "Non-Compliant", "Not Applicable"])
        remarks = st.text_input("Remarks / Findings")
        submitted = st.form_submit_button("➕ Add to Checklist")

    if submitted and item:
        st.session_state.audit_items.append({
            "Item": item,
            "Status": result,
            "Remarks": remarks
        })

    if st.session_state.audit_items:
        st.subheader("✅ Current Audit Checklist")
        df = pd.DataFrame(st.session_state.audit_items)

        total = len(df)
        compliant = len(df[df["Status"] == "Compliant"])
        non_compliant = len(df[df["Status"] == "Non-Compliant"])

        compliance_rate = (compliant / total) * 100 if total > 0 else 0

        st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Checklist", df.to_csv(index=False).encode('utf-8'), "quality_audit.csv")
    else:
        st.info("No audit items added yet.")
