# workflows/pm_hub_oil_gas.py
from typing import Dict, Any, List
import streamlit as st

from services.kpis import compute_pm_kpis
from services.gates import GATE_ITEMS, load_gate_state, save_gate_state
from services.milestones import get_done_set, _key
from services.registry import FEL_CARDS, filter_available
from services.utils import go_to_module
from services.overview import render_pm_overview

# --- Rev4 Sprint-1 additions ---
from services import stakeholders as _stake
from services import raci as _raci  # reserved for next step (RACI on artifact detail)
from services import action_center as _ac
from decisionmate_core.schemas import Stakeholder, RACI

from workflows.pm_common.stakeholders import render_stakeholders_panel
from workflows.pm_common.moc import render_moc_panel
from workflows.pm_common.action_tracker import render_action_tracker_panel
# DEBUG: verify common panels import
try:
    from workflows.pm_common.stakeholders import render_stakeholders_panel
    from workflows.pm_common.moc import render_moc_panel
    from workflows.pm_common.action_tracker import render_action_tracker_panel
    _PANELS_IMPORT_OK = True
except Exception as _e:
    _PANELS_IMPORT_OK = False
    _PANELS_IMPORT_ERR = str(_e)

def _chip(label: str) -> None:
    st.markdown(
        (
            "<span style='padding:2px 8px;border-radius:999px;"
            "background:#eef1f5;font-size:12px'>"
            f"{label}</span>"
        ),
        unsafe_allow_html=True,
    )


def _pill(text: str, active: bool) -> None:
    color = "#0d6efd" if active else "#d7dbe4"
    st.markdown(
        (
            "<div style='display:inline-block;padding:6px 12px;"
            f"margin:4px;border-radius:999px;background:{color};"
            "color:white;font-weight:600;'>"
            f"{text}</div>"
        ),
        unsafe_allow_html=True,
    )


def render(T: Dict[str, Any]) -> Dict[str, Any]:
    
    st.warning("DEBUG: entered Oil & Gas PM Hub render()")

    if not _PANELS_IMPORT_OK:
        st.error(f"DEBUG: pm_common import failed → {_PANELS_IMPORT_ERR}")
    else:
        st.success("DEBUG: pm_common panels import OK")

    st.subheader("📌 PM Hub – Oil & Gas (Projects)")

    # --- Sidebar: minimal inputs for snapshot/KPIs ---
    with st.sidebar.expander("📁 Project Data", expanded=True):
        capex = st.number_input("CAPEX (M$)", min_value=0.0, value=50.0)
        opex = st.number_input("OPEX (M$/y)", min_value=0.0, value=5.0)
        schedule_months = st.number_input("Schedule (months)", min_value=0.0, value=24.0)
        risk_score = st.slider("Risk Index", 0.0, 10.0, 4.0)
        fel_stage = st.selectbox("Current FEL Stage", ["FEL1", "FEL2", "FEL3", "FEL4"], index=0)





    # --- KPIs (not shown here; Overview tab will summarize) ---
    _ = compute_pm_kpis(
        {
            "capex": capex,
            "opex": opex,
            "schedule_months": schedule_months,
            "risk_score": risk_score,
        }
    )

    tabs = st.tabs(["Overview", "FEL Swimlane", "Stage-Gate", "Data"])

    # ---------------- Overview ----------------
    with tabs[0]:
        render_pm_overview(
            {
                "capex": capex,
                "opex": opex,
                "schedule_months": schedule_months,
                "risk_score": risk_score,
                "fel_stage": fel_stage,
            }
        )


    st.markdown("### Cross-Industry Panels")
    render_stakeholders_panel()
    render_moc_panel()
    render_action_tracker_panel()

    # ---------------- FEL Swimlane ----------------
    with tabs[1]:
        st.markdown("### FEL Swimlane")
        stages = ["FEL1", "FEL2", "FEL3", "FEL4"]
        cols = st.columns(4)

        # Completion set for current project
        username = st.session_state.get("username", "Guest")
        industry = st.session_state.get("industry", "oil_gas")
        project_id = st.session_state.get("active_project_id")
        namespace = f"{industry}:projects"
        done = get_done_set(username, namespace, project_id) if project_id else set()

        for i, s in enumerate(stages):
            with cols[i]:
                _pill(s, active=(s == fel_stage))
                stage_cards = filter_available(FEL_CARDS.get(s, []))
                stage_total = len(stage_cards)
                stage_done = sum(
                    1 for c in stage_cards if _key(c["module_path"], c["entry"]) in done
                )
                st.caption(f"{stage_done}/{stage_total} ✅")

                if not stage_cards:
                    st.caption("No tools found in this stage.")
                    continue

                for idx, card in enumerate(stage_cards):
                    card_key = _key(card["module_path"], card["entry"])
                    badge = " ✅" if card_key in done else ""
                    st.markdown(f"**{card['title']}{badge}**")
                    st.caption(card["description"])
                    if st.button(f"Open · {card['title']}", key=f"card_{s}_{idx}"):
                        ctx = {
                            "industry": "oil_gas",
                            "mode": "projects",
                            "fel_stage": fel_stage,
                            "card_stage": s,
                            "tool_title": card["title"],  # recent tools log
                        }
                        go_to_module(card["module_path"], card["entry"], ctx)
                    st.divider()

    # ---------------- Stage-Gate ----------------
    with tabs[2]:
        st.markdown("### Stage-Gate")

        username = st.session_state.get("username", "Guest")
        industry = st.session_state.get("industry", "oil_gas")
        project_id = st.session_state.get("active_project_id")

        if not project_id:
            st.info("Select a project to manage gate checklists.")
        else:
            # Default to current FEL stage; allow switching
            fel_list = ["FEL1", "FEL2", "FEL3", "FEL4"]
            default_idx = fel_list.index(fel_stage) if fel_stage in fel_list else 0
            sel = st.selectbox("FEL stage", fel_list, index=default_idx, key="sg_stage_sel")

            items = GATE_ITEMS.get(sel, [])
            state = load_gate_state(username, industry, project_id, sel)
            checked = set(state.get("checked", []))

            # Progress bar
            total = len(items)
            done_cnt = sum(1 for it in items if it in checked)
            pct = int((done_cnt / total) * 100) if total else 0
            st.progress(pct / 100.0, text=f"{done_cnt}/{total} completed ({pct}%)")

            # Checklist
            new_checked: List[str] = []
            for i, it in enumerate(items):
                val = st.checkbox(it, value=(it in checked), key=f"gate_{sel}_{i}")
                if val:
                    new_checked.append(it)

            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                if st.button("Save Gate", key=f"btn_save_gate_{sel}"):
                    save_gate_state(username, industry, project_id, sel, new_checked)
                    st.success("Gate saved.")
                    st.rerun()
            with c2:
                if st.button("Reload", key=f"btn_reload_gate_{sel}"):
                    st.rerun()
            with c3:
                if st.button("Clear All", key=f"btn_clear_gate_{sel}"):
                    save_gate_state(username, industry, project_id, sel, [])
                    st.success("Gate cleared.")
                    st.rerun()

            st.caption("Gate items are saved per project and FEL stage.")

    # ---------------- Data (debug / raw snapshot) ----------------
    with tabs[3]:
        st.markdown("### Snapshot")
        st.json(
            {
                "capex": capex,
                "opex": opex,
                "schedule_months": schedule_months,
                "risk_score": risk_score,
                "fel_stage": fel_stage,
            }
        )

    # Return snapshot to app.py for save/autosave
    return {
        "capex": capex,
        "opex": opex,
        "schedule_months": schedule_months,
        "risk_score": risk_score,
        "fel_stage": fel_stage,
    }
