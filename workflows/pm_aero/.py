import streamlit as st
from services.pm_bridge import save_stage

def run(key=""):
    st.subheader("Program Brief")  # or the card’s title
    annual_aircraft = st.number_input("Annual aircraft", key=f"{key}_aa")
    if st.button("Save snapshot", key=f"{key}_save"):
        save_stage("fel1", {"payload": {"annual_aircraft": annual_aircraft}})
        st.success("Saved")
