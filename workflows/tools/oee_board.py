# workflows/tools/oee_board.py
from __future__ import annotations

from datetime import datetime, date
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Optional persistence / history / nav (graceful fallback)
try:
    from data.firestore import load_project_doc, save_project_doc
except Exception:
    load_project_doc = save_project_doc = None

try:
    from services.history import append_snapshot
except Exception:
    append_snapshot = None

try:
    from services.utils import back_to_hub
except Exception:
    def back_to_hub():
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

LINES = ["Press-1", "Press-2", "Weld-Cell-A", "Weld-Cell-B", "Assembly-1", "Paint-1"]

# ---------- helpers ----------
def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    ops_mode = "daily_ops"
    return f"{industry}:ops:{ops_mode}"

def _safe_doc(username: str, namespace: str, project_id: str, key: str):
    try:
        return load_project_doc(username, namespace, project_id, key) or {}
    except Exception:
        return {}

def _coerce_date_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def _get_andon_downtime(username: str, namespace: str, project_id: str,
                        d0: date, d1: date, lines: list[str]) -> int:
    """
    Prefer the consolidated snapshot; if missing, sum directly from the Andon log.
    """
    # 1) try snapshot
    try:
        industry = namespace.split(":")[0]
        snap_key = f"{industry}_ops_daily_ops"
        snap = _safe_doc(username, namespace, project_id, snap_key)
        dt = int(snap.get("daily_ops", {}).get("andon", {}).get("downtime_min", 0))
        # snapshot is not date-filtered; if it's present we'll use it as fast-path
        if dt > 0:
            return dt
    except Exception:
        pass

    # 2) fallback: Andon raw rows (filter by dates + lines)
    rows = _safe_doc(username, namespace, project_id, "andon_log").get("rows", [])
    if not rows:
        return 0
    df = pd.DataFrame(rows)
    df = _coerce_date_col(df, "Date")
    df["Downtime (min)"] = pd.to_numeric(df.get("Downtime (min)", 0), errors="coerce").fillna(0)
    mask = (df["Date"] >= d0) & (df["Date"] <= d1)
    if lines:
        mask &= df["Line"].isin(lines)
    return int(df.loc[mask, "Downtime (min)"].sum())

def _gauge(val: float, title: str):
    fig, ax = plt.subplots(figsize=(2.8, 2.8))
    ax.axis("equal")
    ax.pie([val, max(0.0, 1.0 - val)], startangle=90, counterclock=False)
    ax.set_title(title)
    st.pyplot(fig)

# ---------- UI ----------
def render(T=None):
    st.title("📊 OEE Board")
    st.caption("Computes Availability, Performance, Quality. Downtime is pulled automatically from Andon.")

    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"

    # Inputs
    with st.expander("Inputs", expanded=True):
        cols = st.columns([2, 2, 1, 1])
        with cols[0]:
            sel_lines = st.multiselect("Lines", LINES, default=LINES, key="oee_lines")
        with cols[1]:
            d_range = st.date_input("Date range", (pd.Timestamp.utcnow().date(), pd.Timestamp.utcnow().date()), key="oee_dates")
            d0, d1 = (d_range if isinstance(d_range, (list, tuple)) else (d_range, d_range))
        with cols[2]:
            planned_min = st.number_input("Planned Production Time (min)", min_value=1, value=480, step=5, key="oee_planned")
        with cols[3]:
            ideal_ct_sec = st.number_input("Ideal Cycle Time (sec/part)", min_value=1, value=60, step=1, key="oee_ict")

        cols2 = st.columns(3)
        with cols2[0]:
            total_count = st.number_input("Total Produced (good + scrap)", min_value=0, value=400, step=10, key="oee_total")
        with cols2[1]:
            scrap_count = st.number_input("Scrap / Defects", min_value=0, value=10, step=1, key="oee_scrap")
        with cols2[2]:
            breaks_min = st.number_input("Breaks (planned) min", min_value=0, value=30, step=5, key="oee_breaks")

    # Pull downtime from Andon (snapshot or raw)
    downtime_min = _get_andon_downtime(username, namespace, project_id, d0, d1, sel_lines)

    # Calculations
    planned_run = max(0, planned_min - breaks_min)
    operating_time = max(0, planned_run - downtime_min)   # minutes
    good_count = max(0, total_count - scrap_count)
    # Availability
    A = (operating_time / planned_run) if planned_run > 0 else 0.0
    # Performance
    ideal_time_min = (ideal_ct_sec * max(total_count, 0)) / 60.0
    P = (ideal_time_min / operating_time) if operating_time > 0 else 0.0
    # clamp
    P = min(P, 1.50)  # cap at 150% to avoid explosion
    # Quality
    Q = (good_count / total_count) if total_count > 0 else 0.0

    OEE = A * P * Q

    st.subheader("KPI")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Downtime (min) — from Andon", downtime_min)
    k2.metric("Availability", f"{A*100:.1f}%")
    k3.metric("Performance", f"{P*100:.1f}%")
    k4.metric("Quality", f"{Q*100:.1f}%")
    k5.metric("OEE", f"{OEE*100:.1f}%")

    g1, g2, g3, g4 = st.columns(4)
    with g1: _gauge(min(max(A, 0.0), 1.0), "Availability")
    with g2: _gauge(min(max(P, 0.0), 1.0), "Performance")
    with g3: _gauge(min(max(Q, 0.0), 1.0), "Quality")
    with g4: _gauge(min(max(OEE, 0.0), 1.0), "OEE")

    st.caption(f"Planned run: {planned_run} min · Operating: {operating_time} min · Ideal time: {ideal_time_min:.1f} min · Good: {good_count}")

    st.divider()
    st.subheader("Save / Load / Export")
    DOC_KEY = "oee_board"
    c1, c2, c3 = st.columns([1,1,2])

    with c1:
        if st.button("💾 Save", key="oee_save"):
            payload = {
                "meta": {
                    "saved_at": datetime.utcnow().isoformat(),
                    "lines": sel_lines, "date_from": str(d0), "date_to": str(d1),
                },
                "inputs": {
                    "planned_min": int(planned_min),
                    "breaks_min": int(breaks_min),
                    "ideal_ct_sec": int(ideal_ct_sec),
                    "total_count": int(total_count),
                    "scrap_count": int(scrap_count),
                },
                "metrics": {
                    "downtime_min": int(downtime_min),
                    "availability": float(A),
                    "performance": float(P),
                    "quality": float(Q),
                    "oee": float(OEE),
                },
            }
            if save_project_doc:
                save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot:
                append_snapshot(username, namespace, project_id, DOC_KEY, payload)

            # refresh consolidated snapshot (daily_ops)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass

            st.success(f"Saved to [{namespace}] / {DOC_KEY}")

    with c2:
        if st.button("📥 Load", key="oee_load"):
            payload = _safe_doc(username, namespace, project_id, DOC_KEY)
            if not payload:
                st.info("No saved OEE data found.")
            else:
                st.info("Loaded last saved OEE run (inputs not auto-filled; shown in metrics below).")
                m = payload.get("metrics", {})
                st.write(m)

    with c3:
        if st.button("↩ Back to Ops Hub", key="oee_back"):
            back_to_hub()
