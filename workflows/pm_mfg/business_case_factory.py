from __future__ import annotations
import math, uuid
from typing import Optional, List, Dict
import pandas as pd
import streamlit as st

# ---- artifact registry (fallback-safe) ----
def _ensure_store(): st.session_state.setdefault("_artifacts_store", {})
def _key(pid, ph): return f"{pid}::{ph}"

def _fallback_save(pid, ph, ws, typ, data, status="Draft", sources=None):
    _ensure_store()
    rec = {"artifact_id": uuid.uuid4().hex, "project_id": pid, "phase_id": ph,
           "workstream": ws, "type": typ, "data": data or {}, "status": status or "Draft",
           "sources": sources or []}
    st.session_state["_artifacts_store"].setdefault(_key(pid, ph), []).append(rec); return rec

def _fallback_get_latest(pid, typ, ph):
    _ensure_store()
    for rec in reversed(st.session_state["_artifacts_store"].get(_key(pid, ph), [])):
        if rec.get("type") == typ: return rec
    return None

try:
    from services.artifact_registry import save_artifact, get_latest  # type: ignore
except Exception:
    save_artifact, get_latest = _fallback_save, _fallback_get_latest

def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    ph  = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    return pid, ph

def run():
    st.title("Business Case — Factory Program")
    st.caption("Capture demand, price/cost, ROM CAPEX/OPEX. Computes payback and rough NPV.")

    pid, ph = _ids()

    # Prefill if you previously saved
    prev = (get_latest(pid, "MFG_Business_Case", ph) or {}).get("data", {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        product = st.text_input("Product family", value=prev.get("product", "Vehicle X"))
        annual_demand = st.number_input("Annual Demand (units)", 0, 10_000_000, value=int(prev.get("annual_demand_units", 200_000)))
    with c2:
        workdays = st.number_input("Workdays / year", 1, 365, value=int(prev.get("workdays", 250)))
        shifts   = st.number_input("Shifts / day", 1, 4, value=int(prev.get("shifts", 2)))
    with c3:
        price = st.number_input("Avg selling price / unit", 0, 1_000_000, value=int(prev.get("price", 25_000)))
        unit_cost = st.number_input("Unit cost (ex-OPEX)", 0, 1_000_000, value=int(prev.get("unit_cost", 19_000)))
    with c4:
        capex_rom = st.number_input("ROM CAPEX", 0, 10_000_000_000, value=int(prev.get("capex_rom", 750_000_000)))
        opex_mo   = st.number_input("OPEX per month", 0, 100_000_000, value=int(prev.get("opex_monthly", 18_000_000)))

    # Rough economics
    gross_margin_unit = max(0, price - unit_cost)
    gross_margin_yr   = gross_margin_unit * annual_demand
    opex_yr           = opex_mo * 12
    cf_yr             = gross_margin_yr - opex_yr
    payback_months    = math.inf if cf_yr <= 0 else max(1, int(round(capex_rom / (cf_yr / 12.0))))

    st.subheader("Economics")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gross margin / unit", f"{gross_margin_unit:,.0f}")
    k2.metric("Gross margin / year", f"{gross_margin_yr:,.0f}")
    k3.metric("OPEX / year", f"{opex_yr:,.0f}")
    k4.metric("Payback (months)", "∞" if math.isinf(payback_months) else payback_months)

    notes = st.text_area("Notes & key assumptions", prev.get("notes",""), height=120)

    if st.button("💾 Save Business Case"):
        data = {
            "product": product,
            "annual_demand_units": annual_demand,
            "workdays": workdays, "shifts": shifts,
            "price": price, "unit_cost": unit_cost,
            "capex_rom": capex_rom, "opex_monthly": opex_mo,
            "gross_margin_unit": gross_margin_unit,
            "gross_margin_year": gross_margin_yr,
            "cashflow_year": cf_yr,
            "payback_months": None if math.isinf(payback_months) else payback_months,
            "notes": notes,
        }
        save_artifact(pid, ph, "PMO", "MFG_Business_Case", data, status="Draft")
        st.success("Saved PMO / MFG_Business_Case (Draft).")
