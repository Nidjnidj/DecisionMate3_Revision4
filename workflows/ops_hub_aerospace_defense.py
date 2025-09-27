# workflows/ops_hub_aerospace_defense.py
from __future__ import annotations
import streamlit as st
from services.registry import OPS_TOOLS
from services.utils import go_to_module

SUBCATEGORIES = ["Aircraft Design", "Satellite Programs", "Defense Systems"]

def render(T=None):
    st.caption("Industry-aware Ops view")
    sub = st.selectbox("Subcategory", SUBCATEGORIES, key="aero_ops_sub")

    mode = st.session_state.get("ops_mode", "daily_ops")
    cards = OPS_TOOLS.get(mode, [])

    st.markdown(f"### Tools for **{mode.replace('_',' ').title()}**")
    for idx, card in enumerate(cards):
        st.subheader(card["title"])
        st.caption(card["description"])
        if st.button(f"Open · {card['title']}", key=f"aero_{mode}_{idx}"):
            ctx = {
                "industry": "aerospace_defense",
                "mode": "ops",
                "ops_mode": mode,
                "subcategory": sub,
                "tool_title": card["title"],
            }
            go_to_module(card["module_path"], card["entry"], ctx)

    return {"industry": "aerospace_defense", "ops_mode": mode, "subcategory": sub}
