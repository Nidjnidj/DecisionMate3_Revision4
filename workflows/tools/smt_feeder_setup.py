# workflows/tools/smt_feeder_setup.py
from __future__ import annotations

from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Optional persistence/history/back (graceful fallback if missing)
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
BANKS = ["A", "B", "C", "D"]

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
        {"Date": today, "Line": "SMT-1", "Product": "Controller-X",
         "Feeder Bank": "A", "Reel ID": "R-1001", "Component": "0402-Res",
         "Slots": "A1", "Setup (min)": 7, "Teardown (min)": 3,
         "Missing Reel": False, "Operator": "Nigar", "Notes": ""},
        {"Date": today, "Line": "SMT-2", "Product": "Module-Y",
         "Feeder Bank": "B", "Reel ID": "R-2450", "Component": "0603-Cap",
         "Slots": "B4", "Setup (min)": 9, "Teardown (min)": 4,
         "Missing Reel": True, "Operator": "Rashad", "Notes": "Short on R-2450"},
    ])

def _metrics(df: pd.DataFrame):
    d = df.copy()
    d = _coerce_num(d, "Setup (min)")
    d = _coerce_num(d, "Teardown (min)")
    setups = int(len(d))
    total_setup = int(d["Setup (min)"].sum())
    avg_setup = round(d["Setup (min)"].mean(), 1) if setups else 0.0
    missing = int(d.get("Missing Reel", False).sum()) if "Missing Reel" in d.columns else 0
    kit_ready_pct = round(100.0 * (1 - (missing / setups)) if setups else 0.0, 1)
    return dict(setups=setups, total_setup=total_setup, avg_setup=avg_setup,
                missing=missing, kit_ready_pct=kit_ready_pct)

def _bar_by_line(df: pd.DataFrame):
    d = _coerce_num(df.copy(), "Setup (min)")
    if d.empty:
        st.info("No data yet.")
        return
    by = d.groupby("Line", dropna=False)["Setup (min)"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(by.index.astype(str), by.values)
    ax.set_title("Total Setup Minutes by Line")
    ax.set_ylabel("Minutes")
    ax.set_xticklabels(by.index.astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def render(T=None):
    if "smt_setup_df" not in st.session_state:
        st.session_state.smt_setup_df = _default_rows()

    st.title("🧰 SMT Feeder Setup Tracker")
    st.caption("Track feeder setup/teardown times, missing reels, and kit readiness.")

    # Filters
    with st.expander("Filters", expanded=False):
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            f_line = st.multiselect("Line", LINES, default=LINES)
        with c2:
            f_bank = st.multiselect("Feeder Bank", BANKS, default=BANKS)
        with c3:
            search = st.text_input("Search (Product/Reel/Component/Operator)", "")

    df = st.session_state.smt_setup_df.copy()
    df = _coerce_date(df, "Date")
    df = _coerce_num(df, "Setup (min)")
    df = _coerce_num(df, "Teardown (min)")

    mask = df["Line"].isin(f_line) & df["Feeder Bank"].isin(f_bank)
    if search.strip():
        q = search.lower()
        mask &= (
            df["Product"].str.lower().str.contains(q, na=False) |
            df["Reel ID"].str.lower().str.contains(q, na=False) |
            df["Component"].str.lower().str.contains(q, na=False) |
            df["Operator"].str.lower().str.contains(q, na=False)
        )
    view = df.loc[mask].reset_index(drop=True)

    # KPIs
    m = _metrics(df)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Setups", m["setups"])
    k2.metric("Total Setup (min)", m["total_setup"])
    k3.metric("Avg Setup (min)", m["avg_setup"])
    k4.metric("Missing Reels", m["missing"])
    k5.metric("Kit Readiness (%)", f"{m['kit_ready_pct']:.1f}")

    st.divider()
    st.subheader("Feeder Setup Events (edit inline)")
    edf = st.data_editor(
        view,
        num_rows="dynamic",
        use_container_width=True,
        key="smt_setup_editor",
        column_config={
            "Date": st.column_config.DateColumn(),
            "Line": st.column_config.SelectboxColumn(options=LINES),
            "Feeder Bank": st.column_config.SelectboxColumn(options=BANKS),
            "Setup (min)": st.column_config.NumberColumn(min_value=0, step=1),
            "Teardown (min)": st.column_config.NumberColumn(min_value=0, step=1),
            "Missing Reel": st.column_config.CheckboxColumn(),
        },
    )
    # merge back
    df.loc[mask, :] = edf.values
    st.session_state.smt_setup_df = df

    st.divider()
    st.subheader("Total Setup Minutes by Line")
    _bar_by_line(df)

    # Save/Load/Back/Export
    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "smt_feeder_setup"

    b1, b2, b3, b4 = st.columns([1,1,1,2])

    with b1:
        if st.button("💾 Save", key="smt_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": (st.session_state.smt_setup_df.assign(
                    Date=pd.to_datetime(st.session_state.smt_setup_df["Date"], errors="coerce").dt.date.astype(str),
                ).to_dict(orient="records")),
                "metrics": _metrics(st.session_state.smt_setup_df),
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
        if st.button("📥 Load", key="smt_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved SMT data found.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                df2 = _coerce_date(df2, "Date")
                df2 = _coerce_num(df2, "Setup (min)")
                df2 = _coerce_num(df2, "Teardown (min)")
                st.session_state.smt_setup_df = df2
                st.success("Loaded SMT data.")

    with b3:
        if st.button("↩ Back to Ops Hub", key="smt_back"):
            back_to_hub()

    with b4:
        out = st.session_state.smt_setup_df.copy()
        out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "smt_feeder_setup.csv", "text/csv")
