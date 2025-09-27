# workflows/pm_common/action_tracker.py
from __future__ import annotations
import streamlit as st
from services import action_center as _ac

_UNIQUE = "rev4_common_actions"

def render_action_tracker_panel():
    with st.expander("✅ Action Tracker", expanded=False):
        items = _ac.list_actions() or []
        if not items:
            st.info("No open actions.")
            return

        for i in items:
            with st.container(border=True):
                st.markdown(f"**{i['title']}**")
                st.caption(f"Type: {i['type']} · Source: {i['source_id']}")
                col1, col2 = st.columns([1, 1])
                with col1:
                    new_notes = st.text_input(
                        "Notes", value=i.get("notes", ""), key=f"{_UNIQUE}_notes_{i['id']}"
                    )
                with col2:
                    if st.button("Mark Done", key=f"{_UNIQUE}_done_{i['id']}"):
                        _ac.complete_action(i["id"])
                        st.rerun()
                _ac.update_action(i["id"], {"notes": new_notes})
