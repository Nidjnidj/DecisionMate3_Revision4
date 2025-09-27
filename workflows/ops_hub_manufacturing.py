# workflows/ops_hub_manufacturing.py
from __future__ import annotations

import streamlit as st
from services.registry import OPS_TOOLS   # our registry (cards with tags)
from services.utils import go_to_module   # opens a tool safely

# === Subcategory options for Manufacturing and a stable key mapping ===
SUBCATEGORIES = [
    "Automotive Plants",
    "Electronics Production Lines",
    "Supply Chain Optimization",
]
SUBCAT_KEY = {
    "Automotive Plants": "automotive",
    "Electronics Production Lines": "electronics",
    "Supply Chain Optimization": "supply_chain",
}

def _visible_for_scope(card: dict, industry: str, subkey: str) -> bool:
    """Card is visible only if its tags include the current industry + subcat."""
    tags = card.get("tags", {})
    inds = tags.get("industries", ["manufacturing"])  # default scope = manufacturing
    subs = tags.get("subcats", ["all"])               # default subcat scope = all
    ok_ind = ("all" in inds) or (industry in inds)
    ok_sub = ("all" in subs) or (subkey in subs)
    return ok_ind and ok_sub

def _normalize(card: dict):
    """Support both 'module' (new) and 'module_path'+'entry' (legacy)."""
    module_path = card.get("module") or card.get("module_path")
    entry = card.get("entry") or "render"
    title = card.get("title", module_path or "Tool")
    desc = card.get("description", "")
    icon = card.get("icon", "")
    return title, desc, icon, module_path, entry

def render(T=None):
    st.caption("Industry-aware Ops view")

    # Subcategory picker
    sub = st.selectbox("Subcategory", SUBCATEGORIES, key="mfg_ops_sub")
    subkey = SUBCAT_KEY.get(sub, "automotive")

    # Which ops mode (daily_ops / small_projects / call_center) is active?
    mode = st.session_state.get("ops_mode", "daily_ops")
    all_cards = OPS_TOOLS.get(mode, [])

    # Apply industry + subcategory filtering
    industry = st.session_state.get("industry", "manufacturing")
    cards = [c for c in all_cards if _visible_for_scope(c, industry, subkey)]

    st.markdown(f"### Tools for {mode.replace('_', ' ').title()}")

    if not cards:
        st.info("No tools for this subcategory yet.")
        return

    # Render the cards
    for c in cards:
        title, desc, icon, module_path, entry = _normalize(c)
        with st.container():
            st.markdown(f"#### {icon} {title}")
            if desc:
                st.caption(desc)
            if module_path:
                if st.button(f"Open · {title}", key=f"open_{module_path}_{entry}"):
                    go_to_module(module_path, entry, {"tool_title": title})
            else:
                st.warning("Missing module path for this card in the registry.")
