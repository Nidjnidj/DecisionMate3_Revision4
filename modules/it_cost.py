# modules/it_cost.py
from __future__ import annotations
import streamlit as st
import math
from typing import Dict, Any, List
from utils.artifact_bridge import save_artifact, get_latest, approve_artifact
from modules.it_contracts import IT_ENGINEERING, IT_SCHEDULE, IT_COST, ITCostModel

def _months_from_schedule(sprint_len_weeks: int, sprints: int) -> int:
    total_weeks = sprint_len_weeks * sprints
    # 4.345 weeks per month average
    return max(1, math.ceil(total_weeks / 4.345))

def run():
    st.subheader("IT · Cost")
    project_id = st.session_state.get("active_project_id", "demo-project")

    eng = get_latest(project_id, IT_ENGINEERING)
    sched = get_latest(project_id, IT_SCHEDULE)
    if not eng or not sched:
        st.warning("Please ensure Engineering and Schedule artifacts exist.")
        return
    if not (eng.get("approved") and sched.get("approved")):
        st.warning("Upstream artifacts are not Approved yet. Approve Engineering and Schedule before Cost.")
        return

    st.info(f"Upstream: {eng['id']} · {sched['id']}")

    # CAPEX seed from business option is already in business case; if needed you can pull it too.
    capex_init = st.number_input("Initial CAPEX (licenses, setup, one-time)", min_value=0.0, value=15000.0, step=500.0)

    st.markdown("**People cost (monthly)**")
    rate_rows = st.number_input("How many roles to rate?", min_value=1, value=len(sched["data"]["resource_plan"]), step=1)
    rates: Dict[str, float] = {}
    for i in range(rate_rows):
        with st.expander(f"Role #{i+1}", expanded=(i<2)):
            role = (sched["data"]["resource_plan"][i]["role"] if i < len(sched["data"]["resource_plan"]) else f"Role{i+1}")
            role = st.text_input("Role", value=role, key=f"it_cost_role_{i}")
            monthly_rate = st.number_input("Monthly rate (one FTE)", min_value=0.0, value=4000.0, step=100.0, key=f"it_cost_rate_{i}")
            rates[role] = monthly_rate

    cloud = st.number_input("Cloud (monthly)", min_value=0.0, value=1200.0, step=100.0)
    support = st.number_input("Support tools (monthly)", min_value=0.0, value=300.0, step=50.0)

    months = _months_from_schedule(
        int(sched["data"]["sprint_length_weeks"]),
        int(sched["data"]["number_of_sprints"])
    )
    st.write(f"**Derived delivery window:** ~{months} month(s)")

    # Compute monthly OPEX from resource plan and rates
    people_total = 0.0
    for rp in sched["data"]["resource_plan"]:
        role = rp["role"]
        fte = float(rp["FTE"])
        rate = float(rates.get(role, 0.0))
        people_total += fte * rate

    opex_month = {
        "cloud": float(cloud),
        "support": float(support),
        "people": round(people_total, 2)
    }
    opex_sum = sum(opex_month.values())

    # 12 & 36 month totals (simple flat projection)
    total_12m = capex_init + (opex_sum * min(12, months))
    total_36m = capex_init + (opex_sum * min(36, months))

    st.write(f"**Monthly OPEX (computed):** {opex_month} → **{opex_sum:.2f} USD**/mo")
    st.write(f"**TCO 12m:** {total_12m:.2f} USD, **TCO 36m:** {total_36m:.2f} USD")

    # Burn curve (simple): month 1 includes CAPEX; others just OPEX until delivery window ends
    burn_curve: List[Dict[str, Any]] = []
    cum = 0.0
    for m in range(1, months+1):
        capex = capex_init if m == 1 else 0.0
        opex = opex_sum
        cum += (capex + opex)
        burn_curve.append({"month_index": m, "capex": capex, "opex_total": opex, "cum": round(cum, 2)})

    if st.button("Save Cost Model", type="primary"):
        payload = ITCostModel(
            capex_init=float(capex_init),
            opex_per_month=opex_month,
            months=months,
            total_12m=round(total_12m, 2),
            total_36m=round(total_36m, 2),
            burn_curve=burn_curve,
            upstream_refs=[eng["id"], IT_ENGINEERING, sched["id"], IT_SCHEDULE],
        ).to_dict()
        rec = save_artifact(project_id, IT_COST, payload, stage="Cost")
        st.success(f"Saved Cost Model (id: {rec['id']}).")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Approve Cost ✅"):
            if approve_artifact(project_id, IT_COST):
                st.success("Cost model approved.")
            else:
                st.warning("Nothing to approve yet.")
    with c2:
        st.info("Pipeline complete. ✅")
