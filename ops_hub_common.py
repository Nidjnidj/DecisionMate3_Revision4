# ops_hub_common.py
from __future__ import annotations
from typing import Optional
import importlib
import streamlit as st

def _soft_call_center():
    """Return ops_call_center.run (callable) if present, else None."""
    try:
        mod = importlib.import_module("ops_call_center")
        fn = getattr(mod, "run", None)
        return fn if callable(fn) else None
    except Exception:
        return None

def _section_title(title: str):
    st.markdown(f"### {title}")

def _render_daily_ops(industry_key: str, label: str):
    _section_title(f"Daily Ops — {label}")
    st.info("Daily Ops dashboard placeholder. Wire your metrics here (incidents, downtime, SLAs, crew status, etc.).")
    col1, col2, col3 = st.columns(3)
    col1.metric("Open Incidents", 0)
    col2.metric("On-time Tasks (%)", 100)
    col3.metric("SLA Breaches (7d)", 0)
    st.caption(f"Industry context: `{industry_key}`.")

def _render_small_projects(industry_key: str, label: str):
    _section_title(f"Small Projects — {label}")
    st.info("Kanban/board placeholder for small projects. Replace with your real data source.")
    cols = st.columns(3)
    with cols[0]:
        st.write("**Backlog**")
        st.write("- Scope room refresh")
        st.write("- Replace pump seals")
    with cols[1]:
        st.write("**In-Progress**")
        st.write("- Install LED lights")
    with cols[2]:
        st.write("**Done**")
        st.write("- Survey site A")
    st.caption(f"Industry context: `{industry_key}`.")

def _render_call_center(industry_key: str, label: str):
    _section_title(f"Call Center — {label}")
    run_cc = _soft_call_center()
    if run_cc:
        run_cc(industry_key=industry_key)
    else:
        st.warning("`ops_call_center.py` not found or missing a `run()` function.")

def render_for(industry_key: str,
               label: str,
               *,
               submode: str = "daily_ops",
               industry: Optional[str] = None,
               **kwargs):
    """
    Shared renderer for all Ops Hubs.
    Params match what your dynamic opener passes:
      - industry: selected industry key from the app (optional)
      - submode : 'daily_ops' | 'small_projects' | 'call_center'
    """
    mode = (submode or "").strip() or "daily_ops"

    if mode == "call_center":
        _render_call_center(industry_key or (industry or ""), label)
    elif mode == "small_projects":
        _render_small_projects(industry_key or (industry or ""), label)
    else:
        _render_daily_ops(industry_key or (industry or ""), label)

    # Optional debug:
    st.caption(f"✅ Ops Hub loaded: **{label}** · submode=`{mode}`.")
