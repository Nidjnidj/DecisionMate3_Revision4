# workflows/pm_mfg/demand_forecast.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import uuid
from datetime import date

# ---- artifact registry (real or fallback) ----
def _ensure_fallback(): st.session_state.setdefault("_artifacts_store", {})
def _key(pid, phid): return f"{pid}::{phid}"
def _save_fallback(pid, phid, ws, t, data, status="Draft", sources=None):
    _ensure_fallback()
    rec = {
        "artifact_id": uuid.uuid4().hex, "project_id": pid, "phase_id": phid,
        "workstream": ws, "type": t, "data": data or {}, "status": status or "Draft",
        "sources": sources or [],
    }
    st.session_state["_artifacts_store"].setdefault(_key(pid, phid), []).append(rec); return rec
def _approve_fallback(pid, aid):
    _ensure_fallback()
    for items in st.session_state["_artifacts_store"].values():
        for r in items:
            if r["artifact_id"] == aid and r["project_id"] == pid:
                r["status"] = "Approved"; return
try:
    from services.artifact_registry import save_artifact, approve_artifact  # type: ignore
except Exception:
    save_artifact, approve_artifact = _save_fallback, _approve_fallback  # type: ignore

def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    st.session_state["current_project_id"] = pid
    phid = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    st.session_state["current_phase_id"] = phid
    return pid, phid

def _seasonality_vec(kind: str) -> np.ndarray:
    if kind == "none":
        return np.ones(12)
    if kind == "automotive":
        # holiday dip & summer dip
        v = np.array([0.95, 0.98, 1.00, 1.02, 1.05, 1.03, 0.96, 0.94, 1.04, 1.06, 1.05, 0.92])
        return v / v.mean()
    if kind == "electronics":
        # year-end peak
        v = np.array([0.95, 0.98, 1.00, 1.02, 1.03, 1.02, 1.01, 1.00, 1.02, 1.05, 1.12, 1.30])
        return v / v.mean()
    return np.ones(12)

def run():
    st.title("📈 Demand & Mix Forecast")
    st.caption("Build monthly forecast by model with ramp + optional seasonality. Saves a Demand_Forecast artifact.")

    pid, phid = _ids()

    # Settings
    c1, c2, c3 = st.columns(3)
    with c1:
        start_year = st.number_input("Start year", min_value=2000, max_value=2100, value=date.today().year)
    with c2:
        ramp_months = st.number_input("Ramp to nameplate (months)", min_value=1, max_value=60, value=12)
    with c3:
        season_kind = st.selectbox("Seasonality", ["none", "automotive", "electronics"], index=0)

    # Mix table
    if "df_mix" not in st.session_state:
        st.session_state.df_mix = pd.DataFrame([
            {"Model":"A","Annual @ Nameplate":60000},
            {"Model":"B","Annual @ Nameplate":40000},
        ])
    st.subheader("Mix @ nameplate")
    mix = st.data_editor(
        st.session_state.df_mix, key="mix_editor", num_rows="dynamic", use_container_width=True,
        column_config={"Annual @ Nameplate": st.column_config.NumberColumn(min_value=0, step=1000)}
    )
    st.session_state.df_mix = mix

    # Build 12-month profile (first year)
    total_nameplate = float(pd.to_numeric(mix["Annual @ Nameplate"], errors="coerce").fillna(0).sum())
    st.metric("Total nameplate (units/year)", f"{int(total_nameplate):,}")

    months = pd.period_range(f"{start_year}-01", periods=12, freq="M").to_timestamp()
    season = _seasonality_vec(season_kind)

    profiles = {}
    for _, r in mix.iterrows():
        model = str(r["Model"])
        cap = float(r["Annual @ Nameplate"])  # units/yr at nameplate
        # linear ramp
        ramp_curve = np.minimum(1.0, np.arange(1, 13) / float(ramp_months))
        # monthly base (cap/12), apply seasonality then ramp
        monthly = (cap / 12.0) * season * ramp_curve
        profiles[model] = monthly

    df = pd.DataFrame({"Month": months})
    for m, arr in profiles.items():
        df[m] = arr
    df["Total"] = df.drop(columns=["Month"]).sum(axis=1)

    st.subheader("First 12-month forecast")
    st.dataframe(df.set_index("Month"), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Demand_Forecast (Draft)"):
            rec = save_artifact(
                pid, phid, "PMO", "Demand_Forecast",
                {"start_year": int(start_year), "ramp_months": int(ramp_months),
                 "seasonality": season_kind, "mix": mix.to_dict("records"),
                 "monthly": df.to_dict("records")},
                status="Draft"
            )
            st.success(f"Saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve Demand_Forecast"):
            rec = save_artifact(
                pid, phid, "PMO", "Demand_Forecast",
                {"start_year": int(start_year), "ramp_months": int(ramp_months),
                 "seasonality": season_kind, "mix": mix.to_dict("records"),
                 "monthly": df.to_dict("records")},
                status="Pending"
            )
            approve_artifact(pid, rec.get("artifact_id")); st.success("Demand_Forecast Approved.")
