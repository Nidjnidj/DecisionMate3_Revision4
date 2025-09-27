# workflows/pm_mfg/business_case.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import uuid

# ----------------- simple artifact registry (fallback if your service isn't wired) -----------------
def _ensure_fallback():
    st.session_state.setdefault("_artifacts_store", {})

def _key(project_id: str, phase_id: str) -> str:
    return f"{project_id}::{phase_id}"

def _save_fallback(project_id: str, phase_id: str, workstream: str, a_type: str, data: dict,
                   status: str = "Draft", sources: list[str] | None = None):
    _ensure_fallback()
    rec = {
        "artifact_id": uuid.uuid4().hex,
        "project_id": project_id, "phase_id": phase_id,
        "workstream": workstream, "type": a_type,
        "data": data or {}, "status": status or "Draft",
        "sources": sources or [],
    }
    st.session_state["_artifacts_store"].setdefault(_key(project_id, phase_id), []).append(rec)
    return rec

def _approve_fallback(project_id: str, artifact_id: str):
    _ensure_fallback()
    for bucket in st.session_state["_artifacts_store"].values():
        for rec in bucket:
            if rec.get("project_id") == project_id and rec.get("artifact_id") == artifact_id:
                rec["status"] = "Approved"
                return

try:
    # If you already have these services, we'll use them. Otherwise we use the fallback above.
    from services.artifact_registry import save_artifact, approve_artifact  # type: ignore
except Exception:
    save_artifact, approve_artifact = _save_fallback, _approve_fallback  # type: ignore

try:
    from services.utils import back_to_hub
except Exception:
    def back_to_hub():
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

# ----------------- helpers -----------------
def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    st.session_state["current_project_id"] = pid
    phid = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    st.session_state["current_phase_id"] = phid
    return pid, phid

def _num(x, default=0.0):
    try:
        v = float(x)
        if np.isnan(v):
            return float(default)
        return float(v)
    except Exception:
        return float(default)

# ----------------- UI -----------------
def run():
    st.title("💼 Business Case — Factory Program")
    st.caption("Screen scenarios, compute revenue/opex/capex economics, and define a first-cut Factory Program. Saves PMO/Business_Case and Engineering/Factory_Program.")

    # -------- Context & time base
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        horizon_years = st.number_input("Horizon (years)", 5, 30, 10, step=1)
    with c2:
        wacc = st.number_input("Discount rate (WACC, %)", 0.0, 100.0, 10.0, step=0.5)
    with c3:
        tax = st.number_input("Tax rate (%)", 0.0, 100.0, 20.0, step=0.5)
    with c4:
        capex = st.number_input("Total Capex (MUSD, rough)", 0.0, 100000.0, 800.0, step=10.0)

    # -------- Product mix (editable)
    st.subheader("Product mix (edit inline)")
    if "bc_mix" not in st.session_state:
        st.session_state.bc_mix = pd.DataFrame([
            {"Model":"A (hatch)","Year 1 (k units)":30,"Year 2 (k units)":40,"Year 3 (k units)":50,"ASP (USD)":22000,"Var cost/unit (USD)":16000},
            {"Model":"B (sedan)","Year 1 (k units)":20,"Year 2 (k units)":30,"Year 3 (k units)":40,"ASP (USD)":26000,"Var cost/unit (USD)":18500},
        ])
    mix = st.data_editor(
        st.session_state.bc_mix, key="bc_mix_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "Model": st.column_config.TextColumn(),
            "Year 1 (k units)": st.column_config.NumberColumn(min_value=0, step=1),
            "Year 2 (k units)": st.column_config.NumberColumn(min_value=0, step=1),
            "Year 3 (k units)": st.column_config.NumberColumn(min_value=0, step=1),
            "ASP (USD)": st.column_config.NumberColumn(min_value=0, step=100),
            "Var cost/unit (USD)": st.column_config.NumberColumn(min_value=0, step=100),
        }
    )
    st.session_state.bc_mix = mix

    # roll-out demand to full horizon (flat after y3 by default)
    years = [f"Year {i}" for i in range(1, horizon_years+1)]
    demand_ku = []
    for i in range(1, horizon_years+1):
        if f"Year {i} (k units)" in mix.columns:
            demand_ku.append(pd.to_numeric(mix[f"Year {i} (k units)"], errors="coerce").fillna(0.0))
        else:
            # hold-flat the last defined year
            demand_ku.append(pd.to_numeric(mix["Year 3 (k units)"] if "Year 3 (k units)" in mix.columns else 0.0,
                                           errors="coerce").fillna(0.0))
    demand_ku = pd.concat(demand_ku, axis=1)
    demand_ku.columns = years

    # economics per year
    asp = pd.to_numeric(mix["ASP (USD)"], errors="coerce").fillna(0.0)
    vcu = pd.to_numeric(mix["Var cost/unit (USD)"], errors="coerce").fillna(0.0)

    revenue_y = []
    gross_y   = []
    for yi, y in enumerate(years, start=1):
        units = demand_ku[y] * 1000.0
        rev = (units * asp).sum() / 1e6   # MUSD
        var = (units * vcu).sum() / 1e6   # MUSD
        gross = rev - var
        revenue_y.append(rev); gross_y.append(gross)

    econ = pd.DataFrame({"Year": years, "Revenue (MUSD)": revenue_y, "Gross margin (MUSD)": gross_y})
    st.subheader("Economics (years 1..N)")
    st.dataframe(econ, use_container_width=True)

    # Opex & working capital (simple levers)
    st.subheader("Operating assumptions")
    o1, o2, o3, o4 = st.columns(4)
    with o1:
        opex_pct_rev = st.number_input("Other opex (% of revenue)", 0.0, 100.0, 8.0, step=0.5)
    with o2:
        wc_pct_rev = st.number_input("Working capital (% of revenue)", 0.0, 100.0, 5.0, step=0.5)
    with o3:
        depr_years = st.number_input("Depreciation (years, straight line)", 1, 40, 15)
    with o4:
        salvage_pct = st.number_input("Salvage (% of capex at end)", 0.0, 100.0, 5.0, step=0.5)

    opex_y = econ["Revenue (MUSD)"] * (opex_pct_rev/100.0)
    depr   = (capex / max(1, depr_years))
    ebit_y = econ["Gross margin (MUSD)"] - opex_y - depr
    tax_y  = np.maximum(0.0, ebit_y) * (tax/100.0)
    npat_y = ebit_y - tax_y

    # cash flow: +depr (non-cash), -ΔWC, -capex (year 0), +salvage final year
    wc_y   = econ["Revenue (MUSD)"] * (wc_pct_rev/100.0)
    d_wc   = wc_y.diff().fillna(wc_y.iloc[0])  # first year increase = full WC
    cf_y   = npat_y + depr - d_wc
    cf = [ -capex ] + cf_y.tolist()
    # salvage at the end:
    cf[-1] += capex * (salvage_pct/100.0)

    # NPV / Payback (rough)
    r = (wacc/100.0)
    npv = sum(cf[t] / ((1+r)**t) for t in range(len(cf)))
    cum = np.cumsum(cf)
    payback = next((i for i, v in enumerate(cum) if v >= 0), None)

    k1, k2, k3 = st.columns(3)
    k1.metric("NPV (MUSD)", f"{npv:,.1f}")
    k2.metric("Payback (years)", payback if payback is not None else "—")
    k3.metric("Peak revenue (MUSD/yr)", f"{econ['Revenue (MUSD)'].max():,.0f}")

    st.divider()

    # -------- Factory program (first cut)
    st.subheader("Factory Program (first cut)")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        shifts = st.number_input("Shifts/day", 1, 4, 2)
    with f2:
        hours_per_shift = st.number_input("Hours/shift", 1.0, 12.0, 8.0, step=0.5)
    with f3:
        days_per_year = st.number_input("Operating days/year", 200, 365, 305)
    with f4:
        target_takt_sec = st.number_input("Target takt (sec/unit)", 20.0, 600.0, 60.0, step=5.0)

    # total annual demand at steady state (use Year 3+ as steady)
    steady_units = (demand_ku["Year 3"] if "Year 3" in demand_ku.columns else demand_ku.iloc[:, -1]).sum() * 1000.0
    avail_sec_per_year = shifts * hours_per_shift * 3600.0 * days_per_year
    line_capacity = max(1.0, avail_sec_per_year / target_takt_sec)
    required_lines = int(np.ceil(steady_units / line_capacity))

    st.write(f"**Implied line capacity** ≈ {line_capacity:,.0f} units/year")
    st.write(f"**Estimated number of final assembly lines** ≈ {required_lines}")

    st.divider()

    # -------- Save / Approve / Back
    pid, phid = _ids()
    cA, cB, cC = st.columns(3)

    with cA:
        if st.button("💾 Save Business_Case (Draft)", key="bc_save"):
            payload = {
                "meta": {"horizon_years": int(horizon_years), "wacc_pct": float(wacc), "tax_pct": float(tax)},
                "capex_musd": float(capex),
                "econ_table": econ.to_dict(orient="records"),
                "npv_musd": float(npv),
                "payback_years": int(payback) if payback is not None else None,
                "mix_table": st.session_state.bc_mix.to_dict(orient="records"),
                "assumptions": {
                    "opex_pct_rev": float(opex_pct_rev),
                    "wc_pct_rev": float(wc_pct_rev),
                    "depr_years": int(depr_years),
                    "salvage_pct": float(salvage_pct),
                },
            }
            rec = save_artifact(pid, phid, "PMO", "Business_Case", payload, status="Draft")
            st.success(f"Saved Business_Case (id: {rec.get('artifact_id','')[:8]}).")

    with cB:
        if st.button("✅ Approve Business_Case", key="bc_approve"):
            rec = save_artifact(pid, phid, "PMO", "Business_Case",
                                {"note":"Approved business case summary only"}, status="Pending")
            approve_artifact(pid, rec.get("artifact_id"))
            st.success("Business_Case Approved.")

    with cC:
        if st.button("💾 Save Factory_Program (Draft)", key="fp_save"):
            payload = {
                "demand_steady_units": float(steady_units),
                "shifts": int(shifts),
                "hours_per_shift": float(hours_per_shift),
                "days_per_year": int(days_per_year),
                "target_takt_sec": float(target_takt_sec),
                "implied_line_capacity_y": float(line_capacity),
                "estimated_final_assembly_lines": int(required_lines),
            }
            rec = save_artifact(pid, phid, "Engineering", "Factory_Program", payload, status="Draft",
                                sources=["Business_Case"])
            st.success(f"Saved Factory_Program (id: {rec.get('artifact_id','')[:8]}).")

    st.divider()
    if st.button("↩ Back to PM Hub", key="bc_back"):
        back_to_hub()
