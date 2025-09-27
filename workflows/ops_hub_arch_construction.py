import streamlit as st
def render(industry: str = "arch_construction", submode: str = "daily_ops"):
    st.header("🏛️ Ops Hub — Architecture & Construction")
    st.metric("Open RFIs", 0); st.metric("Hot Issues", 0); st.metric("Safety Alerts", 0)
    st.caption("Skeleton ops hub. Wire daily reports and site logs here.")
