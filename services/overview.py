# services/overview.py
from typing import Dict, Any, List
import streamlit as st
from data.firestore import load_project_doc
from services.history import get_history

def _stat(label: str, value: Any):
    c = st.container(border=True)
    c.caption(label)
    c.subheader(f"{value}")

def _trend_section(username: str, namespace: str, project_id: str, doc_key: str):
    hist = get_history(username, namespace, project_id, doc_key)
    if not hist:
        st.info("No history yet. Save a few times to build trends.")
        return
    # Build arrays
    xs = [h["ts"] for h in hist]
    capex = [h["data"].get("capex") for h in hist]
    dur = [h["data"].get("schedule_months") for h in hist]
    # Show simple charts
    st.markdown("#### Trends")
    col1, col2 = st.columns(2)
    with col1:
        st.line_chart({"CAPEX (M$)": capex}, x=xs)
    with col2:
        st.line_chart({"Duration (months)": dur}, x=xs)

def _recent_tools(username: str, namespace: str, project_id: str):
    recent = load_project_doc(username, namespace, project_id, "recent_tools") or {}
    items: List[Dict[str, Any]] = recent.get("items", [])
    st.markdown("#### Recent tools")
    if not items:
        st.caption("No tools opened yet.")
        return
    for it in reversed(items[-6:]):
        title = it.get("title") or it.get("module_path", "module")
        st.write(f"• {title}")

def render_pm_overview(current_snapshot: Dict[str, Any]) -> None:
    username = st.session_state.get("username", "Guest")
    industry = st.session_state.get("industry", "oil_gas")
    mode = "projects"
    project_id = st.session_state.get("active_project_id")
    namespace = f"{industry}:{mode}"

    st.markdown("### Overview")

    meta = st.columns([2, 2, 3, 3])
    _m = {
        "User": username,
        "Project ID": project_id or "— none —",
        "Namespace": namespace,
        "FEL Stage": current_snapshot.get("fel_stage", "—"),
    }
    for (label, val), col in zip(_m.items(), meta):
        with col:
            _stat(label, val)

    st.divider()

    st.markdown("#### KPIs")
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        _stat("CAPEX (M$)", current_snapshot.get("capex", "—"))
    with kpi_cols[1]:
        _stat("OPEX (M$/y)", current_snapshot.get("opex", "—"))
    with kpi_cols[2]:
        _stat("Duration (months)", current_snapshot.get("schedule_months", "—"))
    with kpi_cols[3]:
        _stat("Risk Index", current_snapshot.get("risk_score", "—"))

    st.caption("These are the minimal KPIs from your current PM hub inputs.")

    st.divider()

    fel = current_snapshot.get("fel_stage", "")
    if project_id and fel:
        st.markdown(f"#### Stage-Gate · {fel}")
        try:
            doc_key = f"gate_{fel}"
            gates = load_project_doc(username, namespace, project_id, doc_key) or {}
            checked: List[str] = gates.get("checked", [])
            if checked:
                st.success(f"Completed: {len(checked)} items")
                for item in checked:
                    st.write(f"• {item}")
            else:
                st.info("No gate checklist saved yet for this FEL stage.")
        except Exception as e:
            st.warning(f"Could not load gate status: {e}")
    else:
        st.info("Select a project and set FEL stage to see gate status here.")

    st.divider()

    # Trends + Recent tools (only when a project is selected)
    if project_id:
        with st.expander("📈 Trends", expanded=False):
            _trend_section(username, namespace, project_id, doc_key="projects_overview")
        with st.expander("🧰 Recent tools", expanded=True):
            _recent_tools(username, namespace, project_id)

    with st.expander("Current snapshot JSON", expanded=False):
        st.json(current_snapshot)
