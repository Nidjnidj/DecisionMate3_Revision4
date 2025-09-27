# modules/it_pipeline.py
import streamlit as st
from modules import it_business_case, it_engineering, it_schedule, it_cost

def run():
    st.subheader("IT · Pipeline (Business Case → Engineering → Schedule → Cost)")
    step = st.radio("Stage", ["Business Case","Engineering","Schedule","Cost"], horizontal=True, key="it_stepper")
    st.divider()
    if step == "Business Case":
        it_business_case.run()
    elif step == "Engineering":
        it_engineering.run()
    elif step == "Schedule":
        it_schedule.run()
    elif step == "Cost":
        it_cost.run()
