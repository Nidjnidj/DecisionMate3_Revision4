from __future__ import annotations
import streamlit as st
from ops_hub_common import render_for
from services.registry import OPS_TOOLS
from services.utils import go_to_module

INDUSTRY_KEY = "government_infrastructure"
LABEL = "Government & Infrastructure"

# --- submode renderers (add real UIs whenever you’re ready) ---
def daily_ops():
    st.subheader("Daily Ops — placeholder")
    st.caption("Add your daily ops widgets here (KPIs, incidents, work orders, etc.).")

def small_projects():
    st.subheader("Small Projects — placeholder")

def call_center():
    st.subheader("Call Center — placeholder")
SUBCATEGORIES = ["Metro Systems", "Smart Cities", "Telecom Networks", "Highways"]

def render(T=None):
    st.caption("Industry-aware Ops view")
    sub = st.selectbox("Subcategory", SUBCATEGORIES, key="govinf_ops_sub")

    mode = st.session_state.get("ops_mode", "daily_ops")
    cards = OPS_TOOLS.get(mode, [])

    st.markdown(f"### Tools for **{mode.replace('_',' ').title()}**")
    for idx, card in enumerate(cards):
        st.subheader(card["title"])
        st.caption(card["description"])
        if st.button(f"Open · {card['title']}", key=f"govinf_{mode}_{idx}"):
            ctx = {
                "industry": "government_infrastructure",
                "mode": "ops",
                "ops_mode": mode,
                "subcategory": sub,
                "tool_title": card["title"],
            }
            go_to_module(card["module_path"], card["entry"], ctx)

    return {"industry": "government_infrastructure", "ops_mode": mode, "subcategory": sub}
