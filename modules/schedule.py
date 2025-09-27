import streamlit as st
from ._common import _ensure_deliverable, _mark_deliverable, _set_artifact_status
from artifact_registry import save_artifact
import streamlit as st
from artifact_registry import get_latest, save_artifact
import datetime

DELIV_WBS_BY_STAGE = {
    "FEL1": "WBS (Schedule)",
    "FEL2": "Updated WBS (Schedule)",
    "FEL3": "Level-3 WBS (Schedule)",
    "FEL4": "Execution WBS (Schedule)",
}

DELIV_NET_BY_STAGE = {
    "FEL1": "Schedule Network (Schedule)",
    "FEL2": "Updated Schedule Network (Schedule)",
    "FEL3": "Integrated Schedule (Schedule)",
    "FEL4": "Execution Schedule (Schedule)",
}

ART_WBS = "WBS"
ART_NET = "Schedule_Network"

BENCH = {
    "Pump":      {"proc_cost":  75_000, "install_days": 7,  "lead_weeks": 16},
    "Separator": {"proc_cost": 120_000, "install_days": 14, "lead_weeks": 20},
    "Pipe":      {"proc_cost":  20_000, "install_days": 5,  "lead_weeks": 8},
    "_default":  {"proc_cost":  50_000, "install_days": 10, "lead_weeks": 12},
}

def generate_schedule_from_engineering(project_id: str, phase_id: str):
    """Create WBS + Schedule_Network from Engineering/Equipment_List."""
    equip = get_latest(project_id, "Equipment_List", phase_id)
    if not equip or not equip.get("data") or not equip["data"].get("items"):
        st.warning("No Equipment_List from Engineering. Run the simulator in Engineering and approve it.")
        return
    items = equip["data"]["items"]
    # ... build WBS and Schedule_Network from items ...


    # WBS nodes
    wbs_nodes = [{"id": "1", "parent": None, "name": "Project", "type": "Project", "phase": "FEL", "owner": "PM"}]

    # Activities
    activities = []
    start = datetime.date.today()
    for idx, it in enumerate(items, start=1):
        tag = it.get("tag", f"EQ-{idx}")
        typ = it.get("type", "Equipment")
        bench = BENCH.get(typ, BENCH["_default"])

        wbs_id = f"1.{idx}"
        wbs_nodes.append({
            "id": wbs_id, "parent": "1",
            "name": f"{typ} {tag}", "type": "WP", "phase": "FEL", "owner": "Engineering"
        })

        a_order = {
            "id": f"PO{idx}", "name": f"Order {tag}", "wbs_id": wbs_id,
            "dur_days": int(bench["lead_weeks"] * 7), "predecessors": []
        }
        a_install = {
            "id": f"IN{idx}", "name": f"Install {tag}", "wbs_id": wbs_id,
            "dur_days": int(bench["install_days"]), "predecessors": [a_order["id"]]
        }
        activities += [a_order, a_install]

    finish = start + datetime.timedelta(days=sum(a["dur_days"] for a in activities))
    schedule_net = {
        "activities": activities,
        "critical_path_ids": [a["id"] for a in activities],  # placeholder
        "start_date": start.isoformat(),
        "finish_date": finish.isoformat(),
    }

    save_artifact(project_id, phase_id, "Schedule", "WBS", {"nodes": wbs_nodes}, status="Pending")
    save_artifact(project_id, phase_id, "Schedule", "Schedule_Network", schedule_net, status="Pending")
    st.success("Generated WBS and Schedule_Network from Engineering artifacts.")

def run(stage: str):
    st.header("Schedule")
    d1 = DELIV_WBS_BY_STAGE.get(stage, "WBS")
    d2 = DELIV_NET_BY_STAGE.get(stage, "Schedule Network")

    _ensure_deliverable(stage, d1)
    _ensure_deliverable(stage, d2)
    st.markdown("### Generate from Engineering")
    if st.button("Create WBS & Schedule from Equipment_List"):
        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")
        generate_schedule_from_engineering(project_id, phase_id)

    st.subheader("WBS")
    st.text_area("WBS Structure (JSON or lines)", key=f"wbs_{stage}")

    st.subheader("Network")
    st.text_area("Activities & Logic (CSV/JSON lines)", key=f"net_{stage}")

    col1, col2 = st.columns(2)
    if col1.button("Mark WBS Complete"):
        _mark_deliverable(stage, d1, "Done")
        _set_artifact_status(ART_WBS, "Approved")
        st.success("WBS Approved.")
    if col2.button("Mark Network Complete"):
        _mark_deliverable(stage, d2, "Done")
        _set_artifact_status(ART_NET, "Approved")
        st.success("Schedule Network Approved.")
        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", "PH-FEL1")
        data = {
            "wbs_raw": st.session_state.get(f"wbs_{stage}", ""),
            "network_raw": st.session_state.get(f"net_{stage}", ""),
        }
        save_artifact(project_id, phase_id, "Schedule", ART_NET, data, status="Approved")
