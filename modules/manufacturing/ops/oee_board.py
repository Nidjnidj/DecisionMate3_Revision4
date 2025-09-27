# modules/manufacturing/ops/oee_board.py
from __future__ import annotations
from datetime import date
from typing import Any, Dict

import streamlit as st
import pandas as pd


def run(submode: str | None = None, T: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Manufacturing • Daily Ops • OEE Board.

    Returns a dict snapshot you can store or show later.
    """
    st.header("OEE Board — Manufacturing")

    # --- Inputs
    ops_day = st.date_input("Ops day", value=date.today())

    st.subheader("Inputs")
    c1, c2, c3 = st.columns(3)
    with c1:
        planned_time = st.number_input(
            "Planned production time (min)", min_value=0, max_value=100000, value=480
        )
        downtime = st.number_input(
            "Downtime (min)", min_value=0, max_value=100000, value=45
        )
    with c2:
        ideal_ct = st.number_input(
            "Ideal cycle time per unit (sec)", min_value=0.1, max_value=1_000.0, value=2.5
        )
        total_count = st.number_input("Total count", min_value=0, max_value=1_000_000, value=12000)
    with c3:
        good_count = st.number_input("Good count", min_value=0, max_value=1_000_000, value=11880)
        changeovers = st.number_input("Changeovers (#)", min_value=0, max_value=100, value=2)

    # --- Calculations (standard OEE decomposition)
    operating_time = max(planned_time - downtime, 0)
    availability = 0.0 if planned_time == 0 else operating_time / planned_time
    performance = 0.0 if operating_time == 0 else (total_count * ideal_ct / 60) / operating_time
    quality = 0.0 if total_count == 0 else good_count / total_count
    oee = availability * performance * quality

    # --- KPI tiles
    st.subheader("KPIs")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Availability", f"{availability*100:.1f}%")
    k2.metric("Performance", f"{performance*100:.1f}%")
    k3.metric("Quality", f"{quality*100:.1f}%")
    k4.metric("OEE", f"{oee*100:.1f}%")

    # --- Scrap / defects Pareto (editable starter table)
    st.subheader("Defects / Scrap (Pareto)")
    default_defects = pd.DataFrame(
        {"defect": ["Bent", "Scratch", "Missing part", "Other"], "count": [60, 28, 14, 8]}
    )
    defects_df = st.data_editor(default_defects, num_rows="dynamic", use_container_width=True)

    # --- Return a snapshot dict you can store in session/artifact registry if desired
    return {
        "industry": "manufacturing",
        "ops_mode": "daily_ops",
        "date": str(ops_day),
        "kpis": {
            "availability": availability,
            "performance": performance,
            "quality": quality,
            "oee": oee,
        },
        "inputs": {
            "planned_time_min": planned_time,
            "downtime_min": downtime,
            "ideal_cycle_time_s": ideal_ct,
            "total_count": total_count,
            "good_count": good_count,
            "changeovers": changeovers,
        },
        "defects": defects_df.to_dict(orient="records"),
    }
