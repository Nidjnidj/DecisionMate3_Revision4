import streamlit as st
import pandas as pd

def run(T):
    st.title("📊 HSE KPI Dashboard")

    st.markdown("""
    Input and track key HSE indicators including:
    - **TRIR** (Total Recordable Incident Rate)
    - **LTIFR** (Lost Time Injury Frequency Rate)
    - **Near Misses**
    - **Training Completion Rate**
    """)

    with st.form("kpi_form"):
        hours_worked = st.number_input("Total Hours Worked", min_value=0)
        recordables = st.number_input("Recordable Incidents", min_value=0)
        lost_time_cases = st.number_input("Lost Time Injuries", min_value=0)
        near_misses = st.number_input("Near Misses", min_value=0)
        training_completed = st.number_input("Trainings Completed", min_value=0)
        total_required_training = st.number_input("Total Required Trainings", min_value=1)

        submitted = st.form_submit_button("📥 Calculate KPIs")

    if submitted:
        trir = (recordables / hours_worked * 200000) if hours_worked > 0 else 0
        ltifr = (lost_time_cases / hours_worked * 200000) if hours_worked > 0 else 0
        training_rate = (training_completed / total_required_training * 100) if total_required_training > 0 else 0

        st.subheader("📈 HSE KPI Results")
        st.metric("🔹 TRIR", f"{trir:.2f}")
        st.metric("🔸 LTIFR", f"{ltifr:.2f}")
        st.metric("📌 Near Misses", near_misses)
        st.metric("🎓 Training Completion Rate", f"{training_rate:.1f}%")

        if trir > 3 or ltifr > 2:
            st.warning("⚠️ High incident rate. Review safety controls.")
        elif training_rate < 80:
            st.warning("⚠️ Training compliance is below target.")
        else:
            st.success("✅ HSE performance is within acceptable range.")
