import streamlit as st
from ._common import _ensure_deliverable, _mark_deliverable, _set_artifact_status
from artifact_registry import save_artifact
import streamlit as st
from artifact_registry import get_latest, save_artifact
import datetime

DELIV_BY_STAGE = {
    "FEL1": "Initial Cost Model (Finance)",
    "FEL2": "Refined Cost Model (Finance)",
    "FEL3": "Control Cost Model (Finance)",
    "FEL4": "Final Cost Model (Finance)",
}

ARTIFACT = "Cost_Model"

BENCH = {
    "Pump":      {"proc_cost":  75_000},
    "Separator": {"proc_cost": 120_000},
    "Pipe":      {"proc_cost":  20_000},
    "_default":  {"proc_cost":  50_000},
}

def build_cost_from_engineering_and_schedule(project_id: str, phase_id: str):
    equip = get_latest(project_id, "Equipment_List", phase_id)
    sched = get_latest(project_id, "Schedule_Network", phase_id)

    if not equip or not equip.get("data") or not equip["data"].get("items"):
        st.warning("No Equipment_List found. Run Engineering simulation first.")
        return

    items = equip["data"]["items"]

    # CAPEX from equipment benchmarks
    capex = []
    for idx, it in enumerate(items, start=1):
        typ = it.get("type", "Equipment")
        wbs_id = f"1.{idx}"  # must match the Schedule WBS convention
        bench = BENCH.get(typ, BENCH["_default"])
        capex.append({"wbs_id": wbs_id, "cost": float(bench["proc_cost"])})

    # Cashflow: if schedule exists, pay on PO completion dates; else lump-sum on today
    cashflow = []
    if sched and isinstance(sched.get("data"), dict):
        data = sched["data"]
        acts = data.get("activities", [])
        start_date = data.get("start_date")
        if start_date:
            try:
                start = datetime.date.fromisoformat(start_date)
            except Exception:
                start = datetime.date.today()
        else:
            start = datetime.date.today()

        # Map PO activities by wbs_id (trivial heuristic)
        # For each PO activity, allocate its equipment cost on its finish date
        for a in acts:
            if a.get("id","").startswith("PO"):
                wbs_id = a.get("wbs_id")
                dur = int(a.get("dur_days", 0))
                finish = start + datetime.timedelta(days=dur)
                # find matching capex line
                for c in capex:
                    if c["wbs_id"] == wbs_id:
                        cashflow.append({"date": finish.isoformat(), "outflow": c["cost"], "inflow": 0.0})
                        break
    else:
        today = datetime.date.today().isoformat()
        total = sum(c["cost"] for c in capex)
        cashflow.append({"date": today, "outflow": total, "inflow": 0.0})

    cost_model = {
        "capex_breakdown": capex,
        "opex_breakdown": [],
        "cashflow": cashflow,
        "wacc": 0.10,
    }
    save_artifact(project_id, phase_id, "Finance", "Cost_Model", cost_model, status="Pending")
    st.success("Generated Cost_Model from Engineering/Schedule.")

def run(stage: str):
    st.header("Cost / Finance")
    deliverable = DELIV_BY_STAGE.get(stage, "Cost Model")

    _ensure_deliverable(stage, deliverable)
    st.markdown("### Build Cost from Engineering/Schedule")
    if st.button("Create Cost Model"):
        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")
        build_cost_from_engineering_and_schedule(project_id, phase_id)

    st.subheader("CAPEX")
    total_capex = st.number_input("Total CAPEX (USD)", 0.0, 1e12, 250_000_000.0)
    st.subheader("OPEX")
    total_opex = st.number_input("Annual OPEX (USD/yr)", 0.0, 1e12, 35_000_000.0)

    st.subheader("Economics")
    wacc = st.slider("WACC", 0.0, 0.3, 0.1, 0.01)
    npv = st.number_input("NPV (USD)", -1e12, 1e12, 0.0)

    if st.button("Freeze Cost Model"):
        _mark_deliverable(stage, deliverable, "Done")
        _set_artifact_status(ARTIFACT, "Approved")
        st.success("Cost Model approved.")
        project_id = st.session_state.get("current_project_id", "P-DEMO")
        phase_id   = st.session_state.get("current_phase_id", "PH-FEL1")
        data = {
            "total_capex": total_capex,
            "total_opex": total_opex,
            "wacc": wacc,
            "npv": npv,
        }
        save_artifact(project_id, phase_id, "Finance", ARTIFACT, data, status="Approved")
