# workflows/tools/fpy_dashboard.py
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
try:
    from services.utils import back_to_hub
except Exception:
    def back_to_hub():
        st.session_state.pop("active_view", None)
        st.session_state.pop("module_info", None)
        st.experimental_rerun()

LINES = ["SMT-1", "SMT-2", "SMT-3"]
STATIONS = ["AOI-1", "AOI-2", "ICT", "FCT"]

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:daily_ops"

def _coerce_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def _coerce_num(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

def _default_rows() -> pd.DataFrame:
    today = pd.Timestamp.utcnow().date()
    return pd.DataFrame([
        {"Date": today, "Line": "SMT-1", "Station": "AOI-1", "Units Tested": 500, "Failures": 30, "Defect Type": "Solder bridge"},
        {"Date": today, "Line": "SMT-1", "Station": "ICT",   "Units Tested": 480, "Failures": 10, "Defect Type": "Open"},
        {"Date": today, "Line": "SMT-2", "Station": "AOI-2", "Units Tested": 520, "Failures": 20, "Defect Type": "Tombstoning"},
    ])

def _calc(df: pd.DataFrame):
    d = df.copy()
    d = _coerce_num(d, "Units Tested")
    d = _coerce_num(d, "Failures")
    d["Good"] = (d["Units Tested"] - d["Failures"]).clip(lower=0)
    overall = (d["Good"].sum() / d["Units Tested"].sum()) if d["Units Tested"].sum() > 0 else 0.0
    by_station = (
        d.groupby("Station", dropna=False).agg({"Good":"sum","Units Tested":"sum"})
        .assign(FPY=lambda x: x["Good"] / x["Units Tested"]).fillna(0.0).reset_index()
    )
    by_line = (
        d.groupby("Line", dropna=False).agg({"Good":"sum","Units Tested":"sum"})
        .assign(FPY=lambda x: x["Good"] / x["Units Tested"]).fillna(0.0).reset_index()
    )
    top_defects = (
        d.groupby("Defect Type", dropna=False)["Failures"].sum().sort_values(ascending=False).head(8)
        if "Defect Type" in d.columns else pd.Series(dtype=int)
    )
    return overall, by_station, by_line, top_defects

def _bar_series(series: pd.Series, title: str, ylabel: str):
    if series.empty:
        st.info("No data to chart yet.")
        return
    fig, ax = plt.subplots(figsize=(7,4))
    ax.bar(series.index.astype(str), series.values)
    ax.set_title(title); ax.set_ylabel(ylabel)
    ax.set_xticklabels(series.index.astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def render(T=None):
    if "fpy_df" not in st.session_state:
        st.session_state.fpy_df = _default_rows()

    st.title("🎯 First-Pass Yield (FPY)")
    st.caption("Record tests/failures by station and line, compute FPY by station/line + overall.")

    with st.expander("Filters", expanded=False):
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            f_line = st.multiselect("Line", LINES, default=LINES)
        with c2:
            f_station = st.multiselect("Station", STATIONS, default=STATIONS)
        with c3:
            search = st.text_input("Search (Defect/Station/Line)", "")

    df = st.session_state.fpy_df.copy()
    df = _coerce_date(df, "Date")
    df = _coerce_num(df, "Units Tested")
    df = _coerce_num(df, "Failures")

    mask = df["Line"].isin(f_line) & df["Station"].isin(f_station)
    if search.strip():
        q = search.lower()
        mask &= (
            df["Defect Type"].str.lower().str.contains(q, na=False) |
            df["Station"].str.lower().str.contains(q, na=False) |
            df["Line"].str.lower().str.contains(q, na=False)
        )
    view = df.loc[mask].reset_index(drop=True)

    overall, by_station, by_line, top_defects = _calc(df)
    k1, k2 = st.columns(2)
    k1.metric("Overall FPY", f"{overall*100:.2f}%")
    k2.metric("Total Units", int(df["Units Tested"].sum()))

    st.divider()
    st.subheader("Test Records (edit inline)")
    edf = st.data_editor(
        view,
        num_rows="dynamic",
        use_container_width=True,
        key="fpy_editor",
        column_config={
            "Date": st.column_config.DateColumn(),
            "Line": st.column_config.SelectboxColumn(options=LINES),
            "Station": st.column_config.SelectboxColumn(options=STATIONS),
            "Units Tested": st.column_config.NumberColumn(min_value=0, step=10),
            "Failures": st.column_config.NumberColumn(min_value=0, step=1),
        },
    )
    # merge back
    df.loc[mask, :] = edf.values
    st.session_state.fpy_df = df

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("FPY by Station")
        if not by_station.empty:
            s = by_station.set_index("Station")["FPY"].sort_values(ascending=False)
            _bar_series(s, "FPY by Station", "FPY")
    with c2:
        st.subheader("FPY by Line")
        if not by_line.empty:
            s = by_line.set_index("Line")["FPY"].sort_values(ascending=False)
            _bar_series(s, "FPY by Line", "FPY")

    st.subheader("Top Defects (Failures)")
    if top_defects is not None and len(top_defects) > 0:
        _bar_series(top_defects, "Top Defects", "Failures")
    else:
        st.info("No defects recorded yet.")

    # Save/Load/Back/Export
    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "fpy_dashboard"

    b1, b2, b3, b4 = st.columns([1,1,1,2])

    with b1:
        if st.button("💾 Save", key="fpy_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": (st.session_state.fpy_df.assign(
                    Date=pd.to_datetime(st.session_state.fpy_df["Date"], errors="coerce").dt.date.astype(str),
                ).to_dict(orient="records")),
                "overall_fpy": float(overall),
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

    with b2:
        if st.button("📥 Load", key="fpy_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved FPY data found.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                df2 = _coerce_date(df2, "Date")
                df2 = _coerce_num(df2, "Units Tested")
                df2 = _coerce_num(df2, "Failures")
                st.session_state.fpy_df = df2
                st.success("Loaded FPY data.")

    with b3:
        if st.button("↩ Back to Ops Hub", key="fpy_back"):
            back_to_hub()

    with b4:
        out = st.session_state.fpy_df.copy()
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "fpy_records.csv", "text/csv")
