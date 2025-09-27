# workflows/tools/spc_monitor.py
from __future__ import annotations
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

try:
    from data.firestore import load_project_doc, save_project_doc
except Exception:
    load_project_doc = save_project_doc = None
try:
    from services.history import append_snapshot
except Exception:
    append_snapshot = None

STATIONS = ["Press-1", "Weld-Cell-A", "Assembly-1"]

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:daily_ops"

def _default_rows() -> pd.DataFrame:
    today = pd.Timestamp.utcnow().date()
    return pd.DataFrame([
        {"Date": today, "Station": "Press-1", "Sample": 10.01, "LSL": 9.90, "USL": 10.10},
        {"Date": today, "Station": "Press-1", "Sample": 10.03, "LSL": 9.90, "USL": 10.10},
        {"Date": today, "Station": "Weld-Cell-A", "Sample": 2.02, "LSL": 1.95, "USL": 2.05},
    ])

def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["Date"] = pd.to_datetime(d.get("Date"), errors="coerce").dt.date
    for c in ("Sample","LSL","USL"):
        d[c] = pd.to_numeric(d.get(c, 0), errors="coerce").fillna(0.0)
    return d

def _metrics(d: pd.DataFrame) -> dict:
    if d.empty: return {"stations": 0, "avg_yield": 0.0}
    g = d.groupby("Station")
    within = (d["Sample"].between(d["LSL"], d["USL"])).groupby(d["Station"]).mean()
    avg_yield = float(within.mean()) if not within.empty else 0.0
    return {"stations": int(g.ngroups), "avg_yield": round(100.0 * avg_yield, 1)}

def _trend(d: pd.DataFrame, station: str):
    s = d[d["Station"] == station].sort_values("Date")
    if s.empty:
        st.info("No data for selected station."); return
    fig, ax = plt.subplots(figsize=(7,3.5))
    ax.plot(pd.to_datetime(s["Date"]), s["Sample"], marker="o")
    ax.hlines([s["LSL"].iloc[0], s["USL"].iloc[0]], xmin=pd.to_datetime(s["Date"]).min(),
              xmax=pd.to_datetime(s["Date"]).max(), linestyles="dashed")
    ax.set_title(f"Samples — {station}")
    ax.set_ylabel("Value")
    st.pyplot(fig)

def render(T=None):
    if "spc_df" not in st.session_state:
        st.session_state.spc_df = _default_rows()

    st.title("📈 SPC Monitor (Lite)")
    st.caption("Enter samples, set LSL/USL, see yield by station and a quick trend.")

    with st.expander("Filters", expanded=False):
        c1, c2 = st.columns([1,2])
        with c1: pick = st.selectbox("Trend station", STATIONS, index=0, key="spc_pick")
        with c2: term = st.text_input("Search (Station)", "")

    df = _coerce(st.session_state.spc_df)
    if term.strip():
        df = df[df["Station"].str.lower().str.contains(term.strip().lower(), na=False)]

    m = _metrics(df)
    k1, k2 = st.columns(2)
    k1.metric("Stations", m["stations"]); k2.metric("Avg Yield", f"{m['avg_yield']:.1f}%")

    st.divider()
    st.subheader("Samples (edit inline)")
    edf = st.data_editor(
        df, num_rows="dynamic", use_container_width=True, key="spc_editor",
        column_config={
            "Date": st.column_config.DateColumn(),
            "Station": st.column_config.SelectboxColumn(options=STATIONS),
            "Sample": st.column_config.NumberColumn(step=0.01),
            "LSL": st.column_config.NumberColumn(step=0.01),
            "USL": st.column_config.NumberColumn(step=0.01),
        },
    )
    st.session_state.spc_df = _coerce(edf)

    st.divider()
    st.subheader("Quick Trend")
    _trend(st.session_state.spc_df, st.session_state.get("spc_pick", STATIONS[0]))

    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "spc_monitor"

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("💾 Save", key="spc_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": st.session_state.spc_df.assign(
                    Date=pd.to_datetime(st.session_state.spc_df["Date"], errors="coerce").dt.date.astype(str)
                ).to_dict(orient="records"),
                "metrics": _metrics(st.session_state.spc_df),
            }
            if save_project_doc: save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot: append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")

    with c2:
        if st.button("📥 Load", key="spc_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload: st.info("No saved SPC data.")
            else:
                st.session_state.spc_df = _coerce(pd.DataFrame(payload.get("rows", [])))
                st.success("Loaded SPC data.")

    with c3:
        out = st.session_state.spc_df.copy()
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "spc_samples.csv", "text/csv")
