# workflows/pm_mfg/site_selector.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
import uuid

# ---------- artifact registry (real or fallback) ----------
def _ensure_fallback(): st.session_state.setdefault("_artifacts_store", {})
def _k(pid, phid): return f"{pid}::{phid}"

def _save_fallback(pid, phid, ws, t, data, status="Draft", sources=None):
    _ensure_fallback()
    rec = {
        "artifact_id": uuid.uuid4().hex,
        "project_id": pid, "phase_id": phid,
        "workstream": ws, "type": t,
        "data": data or {}, "status": status or "Draft",
        "sources": sources or [],
    }
    st.session_state["_artifacts_store"].setdefault(_k(pid, phid), []).append(rec)
    return rec

def _approve_fallback(pid, aid):
    _ensure_fallback()
    for items in st.session_state["_artifacts_store"].values():
        for r in items:
            if r.get("artifact_id") == aid and r.get("project_id") == pid:
                r["status"] = "Approved"; return

try:
    from services.artifact_registry import save_artifact, approve_artifact  # type: ignore
except Exception:
    save_artifact, approve_artifact = _save_fallback, _approve_fallback  # type: ignore

# ---------- helpers ----------
def _ids():
    pid = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-DEMO"
    st.session_state["current_project_id"] = pid
    phid = st.session_state.get("current_phase_id") or f"PH-{st.session_state.get('fel_stage','FEL1')}"
    st.session_state["current_phase_id"] = phid
    return pid, phid

try:
    from services.utils import back_to_hub
except Exception:
    def back_to_hub():
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

def _latest_factory_sizing_site_acres() -> float | None:
    """If you used the built-in fallback store, pull the last Factory_Sizing.site_acres."""
    try:
        _ensure_fallback()
        pid, phid = _ids()
        bucket = st.session_state["_artifacts_store"].get(_k(pid, phid), [])
        # Search newest-first
        for rec in reversed(bucket):
            if rec.get("type") == "Factory_Sizing" and rec.get("workstream") == "Engineering":
                d = (rec.get("data") or {}).get("derived", {})
                val = d.get("site_acres")
                return float(val) if val is not None else None
    except Exception:
        pass
    return None

def _num(x, default=0.0):
    try: return float(x)
    except Exception: return float(default)

def _norm(series: pd.Series, higher_is_better: bool) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)
    if len(s) == 0: return s.fillna(0.0)
    vmin, vmax = np.nanmin(s), np.nanmax(s)
    if np.isfinite(vmin) and np.isfinite(vmax) and vmax != vmin:
        z = (s - vmin) / (vmax - vmin)
    else:
        z = pd.Series(np.ones(len(s)), index=s.index)  # all same -> neutral 1.0
    return z if higher_is_better else (1.0 - z)

# ---------- UI ----------
def run():
    st.title("📍 Site Selector (Shortlist & Scoring)")
    st.caption("Score candidate sites (cost, logistics, utilities, risk, incentives). Saves PMO/Site_Shortlist and Preferred_Site.")

    # ---- Requirements (try to prefill from Factory_Sizing)
    req_site_ac = _latest_factory_sizing_site_acres()
    st.subheader("Requirements")
    c1, c2, c3 = st.columns(3)
    with c1:
        req_site_ac = st.number_input(
            "Required site size (acres)",
            min_value=0.0, value=float(req_site_ac or 80.0), step=5.0, key="ss_req_site_ac"
        )
    with c2:
        req_power_mw = st.number_input("Required grid power (MW)", min_value=0.0, value=30.0, step=1.0, key="ss_req_pwr")
    with c3:
        req_water_m3d = st.number_input("Required water (m³/day)", min_value=0.0, value=2500.0, step=100.0, key="ss_req_h2o")

    # ---- Candidate table
    st.subheader("Candidate sites (edit inline)")
    if "ss_sites" not in st.session_state:
        st.session_state.ss_sites = pd.DataFrame([
            {"Site":"Aksaray","Country":"TR","Site acres":120,"Land cost (MUSD)":35,
             "Grid power (MW)":50,"Water (m3/day)":4000,"Dist to port (km)":320,"Dist to OEM (km)":180,
             "Labor index (1=cheap)":3,"Risk index (1=low)":3,"Incentives (MUSD)":25},
            {"Site":"Ploiești","Country":"RO","Site acres":95,"Land cost (MUSD)":28,
             "Grid power (MW)":35,"Water (m3/day)":3000,"Dist to port (km)":230,"Dist to OEM (km)":120,
             "Labor index (1=cheap)":4,"Risk index (1=low)":4,"Incentives (MUSD)":18},
            {"Site":"Tata","Country":"HU","Site acres":85,"Land cost (MUSD)":33,
             "Grid power (MW)":40,"Water (m3/day)":2600,"Dist to port (km)":410,"Dist to OEM (km)":90,
             "Labor index (1=cheap)":5,"Risk index (1=low)":3,"Incentives (MUSD)":30},
        ])
    sites = st.data_editor(
        st.session_state.ss_sites, key="ss_sites_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "Site": st.column_config.TextColumn(),
            "Country": st.column_config.TextColumn(),
            "Site acres": st.column_config.NumberColumn(min_value=0.0, step=1.0),
            "Land cost (MUSD)": st.column_config.NumberColumn(min_value=0.0, step=1.0),
            "Grid power (MW)": st.column_config.NumberColumn(min_value=0.0, step=1.0),
            "Water (m3/day)": st.column_config.NumberColumn(min_value=0.0, step=10.0),
            "Dist to port (km)": st.column_config.NumberColumn(min_value=0.0, step=5.0),
            "Dist to OEM (km)": st.column_config.NumberColumn(min_value=0.0, step=5.0),
            "Labor index (1=cheap)": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Risk index (1=low)": st.column_config.NumberColumn(min_value=1, max_value=10, step=1),
            "Incentives (MUSD)": st.column_config.NumberColumn(min_value=0.0, step=1.0),
        }
    )
    st.session_state.ss_sites = sites

    # ---- Weights
    st.subheader("Weights")
    w1, w2, w3, w4, w5, w6, w7 = st.columns(7)
    with w1: w_cost = st.number_input("Cost", min_value=0, max_value=100, value=25, step=1, key="w_cost")
    with w2: w_log  = st.number_input("Logistics", min_value=0, max_value=100, value=20, step=1, key="w_log")
    with w3: w_util = st.number_input("Utilities", min_value=0, max_value=100, value=20, step=1, key="w_util")
    with w4: w_lbr  = st.number_input("Labor", min_value=0, max_value=100, value=10, step=1, key="w_lbr")
    with w5: w_risk = st.number_input("Risk", min_value=0, max_value=100, value=15, step=1, key="w_risk")
    with w6: w_inct = st.number_input("Incentives", min_value=0, max_value=100, value=10, step=1, key="w_inct")
    with w7: st.caption("Weights need not sum to 100 — we will normalize.")

    # ---- Scoring
    if sites.empty:
        st.info("Add at least one site to compute a score.")
        best_row, score_df = None, pd.DataFrame()
    else:
        df = sites.copy()

        # Capacity fit penalties (fail hard if size/utilities are insufficient)
        df["Fits size"]  = df["Site acres"]     >= req_site_ac
        df["Fits power"] = df["Grid power (MW)"]>= req_power_mw
        df["Fits water"] = df["Water (m3/day)"] >= req_water_m3d

        # Normalize individual factors
        sc_cost  = _norm(df["Land cost (MUSD)"], higher_is_better=False)
        sc_port  = _norm(df["Dist to port (km)"], higher_is_better=False)
        sc_oem   = _norm(df["Dist to OEM (km)"],  higher_is_better=False)
        sc_util  = (_norm(df["Grid power (MW)"], True) + _norm(df["Water (m3/day)"], True)) / 2.0
        sc_lbr   = _norm(df["Labor index (1=cheap)"], higher_is_better=False)
        sc_risk  = _norm(df["Risk index (1=low)"],    higher_is_better=False)
        sc_inct  = _norm(df["Incentives (MUSD)"],     higher_is_better=True)
        sc_log   = (sc_port + sc_oem) / 2.0

        # Combine with weights
        wsum = float(w_cost + w_log + w_util + w_lbr + w_risk + w_inct) or 1.0
        score = (
            sc_cost * (w_cost/wsum) +
            sc_log  * (w_log/wsum)  +
            sc_util * (w_util/wsum) +
            sc_lbr  * (w_lbr/wsum)  +
            sc_risk * (w_risk/wsum) +
            sc_inct * (w_inct/wsum)
        )

        score_df = df.copy()
        score_df["Score"] = np.round(score, 3)
        # Hard filter: any requirement that fails → big penalty
        mask_ok = df["Fits size"] & df["Fits power"] & df["Fits water"]
        score_df.loc[~mask_ok, "Score"] = score_df.loc[~mask_ok, "Score"] * 0.01  # nearly zero

        score_df = score_df.sort_values("Score", ascending=False).reset_index(drop=True)
        st.subheader("Ranking")
        st.dataframe(score_df, use_container_width=True)

        best_row = score_df.iloc[0] if len(score_df) else None
        if best_row is not None:
            st.success(
                f"Recommended: **{best_row['Site']}, {best_row['Country']}**  "
                f"(Score: {best_row['Score']:.3f})"
            )

    # ---- Save / Approve / Export / Back
    pid, phid = _ids()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("💾 Save Site_Shortlist (Draft)", key="site_save"):
            payload = {
                "requirements": {
                    "site_acres": float(req_site_ac),
                    "grid_mw": float(req_power_mw),
                    "water_m3d": float(req_water_m3d),
                },
                "weights": {
                    "cost": int(w_cost), "logistics": int(w_log), "utilities": int(w_util),
                    "labor": int(w_lbr), "risk": int(w_risk), "incentives": int(w_inct),
                },
                "candidates": st.session_state.ss_sites.to_dict("records"),
                "ranking": score_df.to_dict("records"),
            }
            rec = save_artifact(pid, phid, "PMO", "Site_Shortlist", payload, status="Draft")
            st.success(f"Saved (id: {rec.get('artifact_id','')[:8]}…).")
    with c2:
        if st.button("✅ Approve Preferred_Site", key="site_approve"):
            payload = {
                "shortlist_id": None,  # optional: link to shortlist if you want
                "recommended": (best_row.to_dict() if best_row is not None else {}),
            }
            rec = save_artifact(pid, phid, "PMO", "Preferred_Site", payload, status="Pending", sources=["Site_Shortlist"])
            approve_artifact(pid, rec.get("artifact_id"))
            st.success("Preferred_Site Approved.")
    with c3:
        if st.button("Export shortlist (CSV)", key="site_csv"):
            st.download_button(
                "Download CSV",
                data=st.session_state.ss_sites.to_csv(index=False).encode("utf-8"),
                file_name="site_shortlist.csv", mime="text/csv"
            )
    with c4:
        if st.button("↩ Back to PM Hub", key="site_back"):
            back_to_hub()
