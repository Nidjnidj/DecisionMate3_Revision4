import streamlit as st
import pandas as pd

def run(T):
    st.title("🔧 Welding & NDT Tracker")

    st.markdown("""
    Track welding joints and their NDT (Non-Destructive Testing) status.
    Supports RT, UT, MPI, DPI and repair tracking.
    """)

    if "weld_log" not in st.session_state:
        st.session_state.weld_log = []

    with st.form("weld_form"):
        weld_id = st.text_input("Weld ID")
        ndt_method = st.selectbox("NDT Method", ["RT", "UT", "MPI", "DPI", "Visual"])
        result = st.selectbox("Result", ["Accepted", "Rejected"])
        repaired = st.selectbox("Repair Status", ["Not Required", "Repaired", "Pending Repair"])
        remarks = st.text_input("Remarks")

        submitted = st.form_submit_button("➕ Add Weld Record")

    if submitted and weld_id:
        st.session_state.weld_log.append({
            "Weld ID": weld_id,
            "NDT Method": ndt_method,
            "Result": result,
            "Repair Status": repaired,
            "Remarks": remarks
        })

    if st.session_state.weld_log:
        st.subheader("📋 Welding & NDT Log")
        df = pd.DataFrame(st.session_state.weld_log)
        st.dataframe(df, use_container_width=True)

        repair_rate = (
            len(df[df["Repair Status"] == "Repaired"]) / len(df) * 100
            if len(df) > 0 else 0
        )
        st.metric("🔁 Repair Ratio", f"{repair_rate:.1f}%")

        st.download_button("📥 Download Log", df.to_csv(index=False).encode('utf-8'), "welding_ndt_log.csv")
