import streamlit as st
import pandas as pd

def run(T):
    st.title("🧾 Inspection & Test Plan (ITP) Generator")

    st.markdown("""
    Define inspection activities, responsible parties, and inspection types:
    - **Hold Point** (H)
    - **Witness Point** (W)
    - **Review Point** (R)
    """)

    with st.form("itp_form"):
        activity = st.text_input("Activity / Step Description")
        responsible = st.text_input("Responsible Party")
        inspection_type = st.selectbox("Inspection Type", ["Hold", "Witness", "Review"])
        submit = st.form_submit_button("➕ Add to ITP")

    if "itp_table" not in st.session_state:
        st.session_state.itp_table = []

    if submit and activity and responsible:
        st.session_state.itp_table.append({
            "Activity": activity,
            "Responsible": responsible,
            "Type": inspection_type
        })

    if st.session_state.itp_table:
        df = pd.DataFrame(st.session_state.itp_table)
        st.subheader("📋 Current ITP Table")
        st.dataframe(df, use_container_width=True)
        st.download_button("📤 Download as Excel", df.to_csv(index=False).encode('utf-8'), file_name="ITP_Table.csv")

    else:
        st.info("No ITP items added yet.")
