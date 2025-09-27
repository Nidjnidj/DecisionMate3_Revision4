# ai_optimizer.py
"""
DecisionMate — AI Optimizer (Cost • Schedule • Economics • Emissions • NPV + Pareto)

WHAT'S NEW
- Real NPV: Build per-period cash flows (revenues - costs), discount, and report NPV.
- Revenue inputs:
    A) Upload revenues.csv with columns: period_index, revenue_usd
    B) Or set a constant revenue_per_active_day and mark production tasks.
- Pareto Sweep: Try multiple weight combinations, compute metrics, and show non-dominated (Pareto) frontier.

Install once:
    pip install pulp
"""

from __future__ import annotations
import io, json, math, uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st
import pandas as pd
import numpy as np

# ---------- Solver ----------
try:
    import pulp  # pip install pulp
    _PULP_OK = True
except Exception:
    _PULP_OK = False

# ---------- App services ----------
from .providers import get_chat_callable
from .tools import collect_phase_context, format_context_text

# ---------- Namespaced keys ----------
if "AI_OPT_NS" not in st.session_state:
    st.session_state["AI_OPT_NS"] = f"opt_{uuid.uuid4().hex[:8]}"

def k(group: str, name: str) -> str:
    return f"{st.session_state['AI_OPT_NS']}::{group}::{name}"

# ---------- Data models ----------
@dataclass
class Task:
    task_id: str
    name: str
    duration_days: int
    earliest_start: Optional[str] = None  # (not enforced v1)
    latest_finish: Optional[str] = None   # (not enforced v1)
    resource: Optional[str] = None
    resource_qty: float = 0.0
    capex_usd: float = 0.0               # one-time at start
    opex_usd_per_day: float = 0.0
    emissions_tCO2e_per_day: float = 0.0
    predecessor_ids: Optional[List[str]] = None
    is_production: bool = False          # NEW: marks tasks as revenue-generating when active

@dataclass
class Finance:
    discount_rate: float = 0.1           # annual
    commodity_price: float = 0.0
    tax_rate: float = 0.0
    hurdle_rate: float = 0.1

# ---------- Parsing ----------
def parse_tasks(df: pd.DataFrame) -> Dict[str, Task]:
    out: Dict[str, Task] = {}
    if df.empty:
        return out
    for _, r in df.iterrows():
        preds = []
        if pd.notna(r.get("predecessor_ids")) and str(r.get("predecessor_ids")).strip():
            preds = [p.strip() for p in str(r["predecessor_ids"]).split(",") if p.strip()]
        is_prod = False
        val = r.get("is_production")
        if pd.notna(val):
            s = str(val).strip().lower()
            is_prod = s in ("1", "true", "yes", "y")
        t = Task(
            task_id=str(r["task_id"]),
            name=str(r.get("name", "")),
            duration_days=int(r.get("duration_days", 0) or 0),
            earliest_start=str(r.get("earliest_start")) if pd.notna(r.get("earliest_start")) else None,
            latest_finish=str(r.get("latest_finish")) if pd.notna(r.get("latest_finish")) else None,
            resource=str(r.get("resource")) if pd.notna(r.get("resource")) else None,
            resource_qty=float(r.get("resource_qty", 0.0) or 0.0),
            capex_usd=float(r.get("capex_usd", 0.0) or 0.0),
            opex_usd_per_day=float(r.get("opex_usd_per_day", 0.0) or 0.0),
            emissions_tCO2e_per_day=float(r.get("emissions_tCO2e_per_day", 0.0) or 0.0),
            predecessor_ids=preds or None,
            is_production=is_prod,
        )
        out[t.task_id] = t
    return out

def periods_from_schedule(tasks: Dict[str, Task], calendar_step_days: int = 7) -> List[int]:
    horizon_days = int(sum(max(1, t.duration_days) for t in tasks.values()) * 1.5) or 1
    steps = max(1, math.ceil(horizon_days / calendar_step_days))
    return list(range(steps))  # 0..T-1

# ---------- AI helper ----------
def ai_propose_weights_and_constraints(ctx_text: str) -> Dict:
    llm = get_chat_callable()
    system = (
        "You are an optimization strategist. Choose weights summing to 1.0 for:\n"
        "- w_npv (maximize NPV), w_cost (min cost), w_makespan (min makespan), w_emissions (min CO2e)\n"
        "Extract any hard constraints (deadlines, budget caps). Return strict JSON."
    )
    user = f"""
PROJECT CONTEXT (summarized):
{ctx_text}

Return JSON with:
{{
  "weights": {{"w_npv": 0.4, "w_cost": 0.2, "w_makespan": 0.3, "w_emissions": 0.1}},
  "hard_constraints": [
    {{"type": "deadline", "task_id": "FID", "period_index": 8}},
    {{"type": "budget_cap", "period_index": 1, "cap_usd": 30000000}}
  ],
  "notes": "Short reasoning"
}}
"""
    try:
        raw = llm(user, system)
        s = raw.strip()
        start, end = s.find("{"), s.rfind("}")
        js = s[start:end+1] if start != -1 and end != -1 else "{}"
        data = json.loads(js) if js else {}
        w = data.get("weights", {})
        tot = sum(float(w.get(k, 0.0)) for k in ["w_npv", "w_cost", "w_makespan", "w_emissions"]) or 1.0
        for kk in ("w_npv", "w_cost", "w_makespan", "w_emissions"):
            w[kk] = float(w.get(kk, 0.0)) / tot
        return {
            "weights": w or {"w_npv": 0.4, "w_cost": 0.2, "w_makespan": 0.3, "w_emissions": 0.1},
            "hard_constraints": data.get("hard_constraints", []),
            "notes": data.get("notes", "")
        }
    except Exception:
        return {
            "weights": {"w_npv": 0.4, "w_cost": 0.2, "w_makespan": 0.3, "w_emissions": 0.1},
            "hard_constraints": [],
            "notes": "Fallback defaults (LLM parse failed)."
        }

# ---------- MILP ----------
def build_model(
    tasks: Dict[str, Task],
    resources_df: pd.DataFrame,
    budget_df: Optional[pd.DataFrame],
    weights: Dict[str, float],
    hard_constraints: Optional[List[dict]] = None,
    calendar_step_days: int = 7,
):
    if not _PULP_OK:
        raise RuntimeError("PuLP not installed. Run: pip install pulp")

    periods = periods_from_schedule(tasks, calendar_step_days)
    T = len(periods)
    step_days = calendar_step_days

    m = pulp.LpProblem("DecisionMate_Optimizer", pulp.LpMinimize)

    # Vars
    start = pulp.LpVariable.dicts("start", ((t, p) for t in tasks for p in periods), 0, 1, cat="Binary")
    active = pulp.LpVariable.dicts("active", ((t, p) for t in tasks for p in periods), 0, 1, cat="Binary")
    C = {t: pulp.LpVariable(f"C_{t}", lowBound=0) for t in tasks}
    makespan = pulp.LpVariable("makespan", lowBound=0)

    # 1) Each task starts once
    for t_id in tasks:
        m += pulp.lpSum(start[(t_id, p)] for p in periods) == 1, f"one_start_{t_id}"

    # 2) Link active periods to start + duration
    for t_id, t in tasks.items():
        dur_p = math.ceil(max(1, t.duration_days) / step_days)
        for p in periods:
            valid_starts = [s for s in periods if s <= p < s + dur_p]
            if valid_starts:
                m += active[(t_id, p)] >= pulp.lpSum(start[(t_id, s)] for s in valid_starts), f"act_link_{t_id}_{p}"
            else:
                m += active[(t_id, p)] == 0, f"act_zero_{t_id}_{p}"

    # 3) Precedence
    for t_id, t in tasks.items():
        dur_p = math.ceil(max(1, t.duration_days) / step_days)
        m += C[t_id] == pulp.lpSum((p + dur_p) * start[(t_id, p)] for p in periods), f"completion_{t_id}"
    for t_id, t in tasks.items():
        if t.predecessor_ids:
            for pred in t.predecessor_ids:
                if pred in tasks:
                    m += pulp.lpSum(p * start[(t_id, p)] for p in periods) >= C[pred], f"prec_{pred}_{t_id}"

    # 4) Makespan
    for t_id in tasks:
        m += makespan >= C[t_id], f"mk_ge_{t_id}"

    # 5) Resource caps
    if resources_df is not None and not resources_df.empty:
        caps = {str(r.resource): float(r.capacity_qty or 0.0) for _, r in resources_df.iterrows()}
        for p in periods:
            for rname, cap in caps.items():
                m += pulp.lpSum(
                    (tasks[t_id].resource_qty if tasks[t_id].resource == rname else 0.0) * active[(t_id, p)]
                    for t_id in tasks
                ) <= cap, f"cap_{rname}_{p}"

    # 6) Budget caps per period (CAPEX at start)
    if budget_df is not None and not budget_df.empty:
        caps = dict(enumerate(list(budget_df["capex_cap_usd"].astype(float))))
        for p in periods:
            if p in caps:
                m += pulp.lpSum(tasks[t].capex_usd * start[(t, p)] for t in tasks) <= caps[p], f"budget_{p}"

    # 7) Optional AI hard constraints
    hard_constraints = hard_constraints or []
    for hc in hard_constraints:
        try:
            typ = str(hc.get("type", "")).lower()
            if typ == "deadline":
                t_id = hc.get("task_id")
                latest_p = int(hc.get("period_index", T - 1))
                if t_id in tasks:
                    m += C[t_id] <= latest_p + 1, f"deadline_{t_id}"
            elif typ == "budget_cap":
                pidx = int(hc.get("period_index"))
                cap = float(hc.get("cap_usd", 0.0))
                m += pulp.lpSum(tasks[t].capex_usd * start[(t, pidx)] for t in tasks) <= cap, f"ai_budget_{pidx}"
        except Exception:
            pass

    # Objective terms
    tot_capex = pulp.lpSum(tasks[t].capex_usd * start[(t, p)] for t in tasks for p in periods)
    tot_opex = pulp.lpSum(tasks[t].opex_usd_per_day * step_days * active[(t, p)] for t in tasks for p in periods)
    tot_emis = pulp.lpSum(tasks[t].emissions_tCO2e_per_day * step_days * active[(t, p)] for t in tasks for p in periods)

    # We still solve as a combined objective (scalarization). NPV is handled post-solve for metrics & Pareto.
    w_npv = float(weights.get("w_npv", 0.4))
    w_cost = float(weights.get("w_cost", 0.2))
    w_mks = float(weights.get("w_makespan", 0.3))
    w_em  = float(weights.get("w_emissions", 0.1))

    cap_scale = 1e6
    time_scale = 10.0
    emis_scale = 100.0

    # Minimize combined losses; for NPV in-objective we keep the same proxy as before (cost)
    objective = (
        w_cost * ((tot_capex + tot_opex) / cap_scale) +
        w_mks  * (makespan / time_scale) +
        w_em   * (tot_emis / emis_scale) -
        w_npv  * (-(tot_capex + tot_opex) / cap_scale)
    )
    m += objective

    return m, {"start": start, "active": active, "C": C, "makespan": makespan, "periods": periods, "step_days": step_days}

def solve_model(model) -> Tuple[str, float]:
    status = model.solve(pulp.PULP_CBC_CMD(msg=False))
    return pulp.LpStatus[status], pulp.value(model.objective)

def extract_solution(tasks: Dict[str, Task], vars: dict) -> pd.DataFrame:
    start, C, periods, step = vars["start"], vars["C"], vars["periods"], vars["step_days"]
    rows = []
    for t_id, t in tasks.items():
        sp = next((p for p in periods if (pulp.value(start[(t_id, p)]) or 0) > 0.5), 0)
        comp = int(pulp.value(C[t_id]) or 0)
        rows.append({
            "task_id": t_id, "name": t.name,
            "start_period": int(sp), "finish_period": int(comp),
            "start_day": sp * step, "finish_day": comp * step,
            "duration_days": t.duration_days, "resource": t.resource,
            "is_production": t.is_production
        })
    return pd.DataFrame(rows).sort_values(["start_period", "finish_period", "task_id"])

# ---------- Metrics: cashflows & NPV ----------
def cashflow_series(
    tasks: Dict[str, Task],
    sol_df: pd.DataFrame,
    periods: List[int],
    step_days: int,
    revenues_df: Optional[pd.DataFrame],
    revenue_per_active_day: float = 0.0
) -> pd.DataFrame:
    """
    Build period-indexed cashflow table:
      capex_out, opex_out, revenue_in, net_cf
    CAPEX occurs at task start period; OPEX accrues for active periods; Revenue accrues either
    from revenues_df (period_index,revenue_usd) OR from production tasks being active times revenue_per_active_day.
    """
    cf = pd.DataFrame({"period_index": periods, "capex_out": 0.0, "opex_out": 0.0, "revenue_in": 0.0}).set_index("period_index")

    # CAPEX at start period
    for _, r in sol_df.iterrows():
        if r["start_period"] in cf.index:
            cf.loc[r["start_period"], "capex_out"] += float(tasks[r["task_id"]].capex_usd or 0.0)

    # OPEX by active periods
    for _, r in sol_df.iterrows():
        t = tasks[r["task_id"]]
        dur_p = max(1, math.ceil(t.duration_days / step_days))
        for p in range(int(r["start_period"]), int(r["start_period"]) + dur_p):
            if p in cf.index:
                cf.loc[p, "opex_out"] += float(t.opex_usd_per_day or 0.0) * step_days

    # Revenue
    if revenues_df is not None and not revenues_df.empty:
        # explicit revenue per period
        rmap = dict(zip(revenues_df["period_index"].astype(int), revenues_df["revenue_usd"].astype(float)))
        for p, val in rmap.items():
            if p in cf.index:
                cf.loc[p, "revenue_in"] += float(val or 0.0)
    elif revenue_per_active_day > 0:
        # production tasks earn constant revenue while active
        for _, r in sol_df.iterrows():
            t = tasks[r["task_id"]]
            if not t.is_production:
                continue
            dur_p = max(1, math.ceil(t.duration_days / step_days))
            for p in range(int(r["start_period"]), int(r["start_period"]) + dur_p):
                if p in cf.index:
                    cf.loc[p, "revenue_in"] += float(revenue_per_active_day) * step_days

    cf["net_cf"] = cf["revenue_in"] - (cf["capex_out"] + cf["opex_out"])
    cf = cf.reset_index()
    return cf

def npv_from_cashflows(cf_df: pd.DataFrame, discount_rate_annual: float, step_days: int) -> float:
    """Discount net_cf per period using simple discrete discounting aligned to period length."""
    if cf_df.empty:
        return 0.0
    # Convert annual rate to per-period rate
    periods_per_year = max(1.0, 365.0 / float(step_days))
    r = (1.0 + float(discount_rate_annual)) ** (1.0 / periods_per_year) - 1.0
    npv = 0.0
    for _, row in cf_df.iterrows():
        p = int(row["period_index"])
        npv += float(row["net_cf"]) / ((1.0 + r) ** p)
    return float(npv)

# ---------- Pareto Sweep ----------
def weight_grid(n_steps: int = 5) -> List[Dict[str, float]]:
    """
    Create a small grid of weight combos (sum=1) over (w_cost, w_makespan, w_emissions, w_npv).
    We bias toward including some points with higher w_npv and higher w_cost/makespan coverage.
    """
    vals = np.linspace(0.0, 1.0, n_steps)
    combos = []
    for a in vals:
        for b in vals:
            for c in vals:
                d = 1.0 - (a + b + c)
                if d < -1e-9:
                    continue
                d = max(0.0, d)
                s = a + b + c + d
                if s <= 0:
                    continue
                combos.append({
                    "w_cost": a / s,
                    "w_makespan": b / s,
                    "w_emissions": c / s,
                    "w_npv": d / s
                })
    # Deduplicate close ones
    df = pd.DataFrame(combos).round(2).drop_duplicates().to_dict(orient="records")
    return df

def is_dominated(row, df, larger_is_better_cols, smaller_is_better_cols) -> bool:
    """Check Pareto dominance."""
    for _, r in df.iterrows():
        if (r is row) or (r.name == row.name):
            continue
        ge = all(r[c] >= row[c] - 1e-9 for c in larger_is_better_cols)
        le = all(r[c] <= row[c] + 1e-9 for c in smaller_is_better_cols)
        strict_better = any(r[c] > row[c] + 1e-9 for c in larger_is_better_cols) or \
                        any(r[c] < row[c] - 1e-9 for c in smaller_is_better_cols)
        if ge and le and strict_better:
            return True
    return False

# ---------- UI ----------
def render():
    st.title("🧠 AI Optimizer — Cost • Schedule • Economics • Emissions • NPV + Pareto")

    # Context for AI proposals
    pid = st.session_state.get("current_project_id") or "P-DEMO"
    ph = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    ctx_text = format_context_text(collect_phase_context(pid, ph))

    with st.expander("AI proposals (weights & constraints)"):
        if st.button("Ask AI", key=k("ai", "ask")):
            st.session_state[k("ai", "props")] = ai_propose_weights_and_constraints(ctx_text)
        props = st.session_state.get(k("ai", "props"))
        if props:
            st.json(props)

    st.markdown("### 1) Inputs")
    c1, c2, c3 = st.columns(3)
    f_tasks = c1.file_uploader("tasks.csv", type=["csv"], key=k("up","tasks"))
    f_res   = c2.file_uploader("resources.csv", type=["csv"], key=k("up","res"))
    f_bud   = c3.file_uploader("budget.csv (optional)", type=["csv"], key=k("up","bud"))

    c4, c5 = st.columns(2)
    f_rev  = c4.file_uploader("revenues.csv (optional: period_index,revenue_usd)", type=["csv"], key=k("up","rev"))
    revenue_per_active_day = c5.number_input("OR constant revenue per active production task (USD/day)", 0.0, 1e12, 0.0, 1000.0, key=k("up","rev_const"))

    st.caption("TIP: add column `is_production`=true on tasks that generate revenue when active (for the constant revenue option).")

    st.markdown("### 2) Objective weights")
    props_w = (st.session_state.get(k("ai","props")) or {}).get("weights", {})
    w_npv = st.number_input("Weight: Maximize NPV", 0.0, 1.0, float(props_w.get("w_npv", 0.4)), 0.05, key=k("w","npv"))
    w_cost = st.number_input("Weight: Minimize Cost", 0.0, 1.0, float(props_w.get("w_cost", 0.2)), 0.05, key=k("w","cost"))
    w_mks = st.number_input("Weight: Minimize Makespan", 0.0, 1.0, float(props_w.get("w_makespan", 0.3)), 0.05, key=k("w","mks"))
    w_em  = st.number_input("Weight: Minimize Emissions", 0.0, 1.0, float(props_w.get("w_emissions", 0.1)), 0.05, key=k("w","em"))

    st.caption("Weights are normalized internally. Try (NPV 0.4, Cost 0.2, Makespan 0.3, Emissions 0.1).")

    st.markdown("### 3) Run optimization")
    calendar_step_days = st.number_input("Calendar step size (days per period)", 1, 30, 7, 1, key=k("cfg","stepdays"))
    discount_rate = st.number_input("Annual discount rate (for NPV)", 0.0, 1.0, 0.10, 0.005, key=k("cfg","disc"))

    if st.button("Run Optimization", use_container_width=True, key=k("btn","run")):
        # Parse inputs
        try:
            tasks_df = pd.read_csv(f_tasks) if f_tasks else pd.DataFrame()
            res_df   = pd.read_csv(f_res) if f_res else pd.DataFrame()
            bud_df   = pd.read_csv(f_bud) if f_bud else pd.DataFrame()
            rev_df   = pd.read_csv(f_rev) if f_rev else pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to read inputs: {e}")
            return

        if tasks_df.empty or res_df.empty:
            st.error("Please provide tasks.csv and resources.csv.")
            return

        tasks = parse_tasks(tasks_df)
        weights = {"w_npv": w_npv, "w_cost": w_cost, "w_makespan": w_mks, "w_emissions": w_em}
        ssum = sum(weights.values()) or 1.0
        for kk in list(weights):
            weights[kk] = weights[kk] / ssum

        ai_hard = (st.session_state.get(k("ai","props")) or {}).get("hard_constraints", [])

        if not _PULP_OK:
            st.error("PuLP not installed. Run: pip install pulp")
            return

        # Build + solve
        try:
            model, vars_ = build_model(tasks, res_df, bud_df if not bud_df.empty else None, weights, ai_hard, calendar_step_days)
        except Exception as e:
            st.error(f"Model build failed: {e}")
            return

        status, obj = solve_model(model)
        st.write(f"**Solver status:** {status}")
        st.write(f"**Scalarized objective:** {obj:.4f}" if obj is not None else "**Scalarized objective:** (n/a)")
        if status not in ("Optimal", "Feasible"):
            st.warning("Solution not optimal; consider relaxing constraints or adjusting weights.")

        # Extract solution + metrics
        try:
            sol = extract_solution(tasks, vars_)
            st.dataframe(sol, use_container_width=True)
            st.session_state[k("sol","df")] = sol

            periods = vars_["periods"]; step_days = vars_["step_days"]
            cf = cashflow_series(tasks, sol, periods, step_days, rev_df if not rev_df.empty else None, revenue_per_active_day)
            npv_val = npv_from_cashflows(cf, discount_rate_annual=discount_rate, step_days=step_days)

            st.markdown("#### Cashflows by period")
            st.dataframe(cf, use_container_width=True)
            st.success(f"**NPV:** ${npv_val:,.0f}")

            # Quick CSV downloads
            buf1 = io.BytesIO(); sol.to_csv(buf1, index=False)
            st.download_button("Download optimized_schedule.csv", data=buf1.getvalue(), file_name="optimized_schedule.csv", mime="text/csv", key=k("dl","sch"))
            buf2 = io.BytesIO(); cf.to_csv(buf2, index=False)
            st.download_button("Download cashflows.csv", data=buf2.getvalue(), file_name="cashflows.csv", mime="text/csv", key=k("dl","cf"))

        except Exception as e:
            st.error(f"Failed to compute metrics: {e}")

        # Save artifact
        if st.button("Save Optimization as Artifact", key=k("btn","save_art")):
            try:
                from artifact_registry import save
                save(
                    project_id=pid,
                    phase_id=ph,
                    artifact_type="AI_Optimization",
                    data={
                        "weights": weights,
                        "objective_value": obj,
                        "npv": float(npv_val),
                        "schedule": st.session_state.get(k("sol","df")).to_dict(orient="records"),
                        "cashflows": cf.to_dict(orient="records")
                    },
                    status="Draft"
                )
                st.success("Saved as artifact: AI_Optimization (Draft)")
            except Exception as e:
                st.error(f"Could not save artifact: {e}")

    st.markdown("---")
    st.markdown("### 4) Pareto Sweep (explore tradeoffs)")
    n_steps = st.slider("Weight grid granularity", 3, 7, 5, key=k("pareto","steps"))
    if st.button("Run Pareto Sweep", use_container_width=True, key=k("pareto","run")):
        # Inputs again (we reuse current uploads/values from state)
        try:
            f_tasks_state = st.session_state.get(k("up","tasks"))
            f_res_state   = st.session_state.get(k("up","res"))
            f_bud_state   = st.session_state.get(k("up","bud"))
            f_rev_state   = st.session_state.get(k("up","rev"))

            tasks_df = pd.read_csv(f_tasks_state) if f_tasks_state else pd.DataFrame()
            res_df   = pd.read_csv(f_res_state) if f_res_state else pd.DataFrame()
            bud_df   = pd.read_csv(f_bud_state) if f_bud_state else pd.DataFrame()
            rev_df   = pd.read_csv(f_rev_state) if f_rev_state else pd.DataFrame()
        except Exception as e:
            st.error(f"Failed to read inputs for sweep: {e}")
            return

        if tasks_df.empty or res_df.empty:
            st.error("Please provide tasks.csv and resources.csv before running the sweep.")
            return

        tasks = parse_tasks(tasks_df)
        ai_hard = (st.session_state.get(k("ai","props")) or {}).get("hard_constraints", [])
        if not _PULP_OK:
            st.error("PuLP not installed. Run: pip install pulp")
            return

        combos = weight_grid(n_steps=n_steps)
        rows = []
        for w in combos:
            try:
                model, vars_ = build_model(tasks, res_df, bud_df if not bud_df.empty else None, w, ai_hard, st.session_state.get(k("cfg","stepdays"), 7))
                status, obj = solve_model(model)
                if status not in ("Optimal", "Feasible"):
                    continue
                sol = extract_solution(tasks, vars_)
                periods = vars_["periods"]; step_days = vars_["step_days"]
                cf = cashflow_series(tasks, sol, periods, step_days, rev_df if not rev_df.empty else None, st.session_state.get(k("up","rev_const"), 0.0))
                npv_val = npv_from_cashflows(cf, discount_rate_annual=st.session_state.get(k("cfg","disc"), 0.10), step_days=step_days)

                # Collect scalar metrics for the frontier
                cost_val = float(cf["capex_out"].sum() + cf["opex_out"].sum())
                emis_val = float((cf["period_index"] * 0.0).sum())  # optional: compute from solution if needed
                # Better emissions metric: recompute from tasks & activity
                emis_val = 0.0
                for _, r in sol.iterrows():
                    t = tasks[r["task_id"]]
                    dur_p = max(1, math.ceil(t.duration_days / step_days))
                    emis_val += float(t.emissions_tCO2e_per_day or 0.0) * step_days * dur_p
                makespan_val = float(sol["finish_period"].max())

                rows.append({
                    "w_cost": w["w_cost"], "w_makespan": w["w_makespan"], "w_emissions": w["w_emissions"], "w_npv": w["w_npv"],
                    "objective": float(obj) if obj is not None else np.nan,
                    "NPV": npv_val,
                    "TotalCost": cost_val,
                    "MakespanPeriods": makespan_val,
                    "Emissions_tCO2e": emis_val
                })
            except Exception:
                continue

        if not rows:
            st.warning("No feasible points found for the current grid/constraints.")
            return

        res = pd.DataFrame(rows)

        # Pareto filter (maximize NPV; minimize Cost, Makespan, Emissions)
        larger_is_better = ["NPV"]
        smaller_is_better = ["TotalCost", "MakespanPeriods", "Emissions_tCO2e"]
        res["_dominated"] = res.apply(lambda row: is_dominated(row, res, larger_is_better, smaller_is_better), axis=1)
        frontier = res[~res["_dominated"]].copy()

        st.markdown("#### All Sweep Results")
        st.dataframe(res.drop(columns=["_dominated"]), use_container_width=True)
        st.markdown("#### Pareto Frontier (non-dominated)")
        st.dataframe(frontier.drop(columns=["_dominated"]), use_container_width=True)

        # Quick scatter: NPV vs TotalCost (intuitive)
        try:
            st.markdown("##### Quick view: NPV vs Total Cost (Pareto points highlighted)")
            import plotly.express as px  # you likely already use plotly elsewhere
            fig = px.scatter(
                res, x="TotalCost", y="NPV",
                color=res["_dominated"].map({True: "dominated", False: "pareto"}),
                hover_data=["w_cost", "w_makespan", "w_emissions", "w_npv", "MakespanPeriods", "Emissions_tCO2e"]
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass

        # Downloads
        b1 = io.BytesIO(); res.drop(columns=["_dominated"]).to_csv(b1, index=False)
        st.download_button("Download sweep_results.csv", data=b1.getvalue(), file_name="sweep_results.csv", mime="text/csv", key=k("pareto","dl_all"))
        b2 = io.BytesIO(); frontier.drop(columns=["_dominated"]).to_csv(b2, index=False)
        st.download_button("Download pareto_frontier.csv", data=b2.getvalue(), file_name="pareto_frontier.csv", mime="text/csv", key=k("pareto","dl_pf"))

    st.markdown("---")
    st.markdown("#### Input templates")
    st.code(
        json.dumps({
            "tasks.csv columns": [
                "task_id","name","duration_days","resource","resource_qty",
                "capex_usd","opex_usd_per_day","emissions_tCO2e_per_day",
                "predecessor_ids","is_production (true/false)"
            ],
            "resources.csv columns": ["resource","capacity_qty"],
            "budget.csv columns": ["period_index","capex_cap_usd"],
            "revenues.csv columns": ["period_index","revenue_usd"]
        }, indent=2),
        language="json"
    )
