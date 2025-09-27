# workflows/tools/shift_huddle.py
from __future__ import annotations
from datetime import datetime
import pandas as pd
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

SHIFTS = ["A", "B", "C"]
PRIORITY = ["P1", "P2", "P3"]
STATUS = ["Open", "In Progress", "Blocked", "Done"]

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:daily_ops"

def _coerce_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns: df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def _default_rows() -> pd.DataFrame:
    today = pd.Timestamp.utcnow().date()
    return pd.DataFrame([
        {"Date": today, "Shift": "A", "Area": "Assembly-1", "Priority": "P1", "Item": "Safety gate interlock check",
         "Owner": "Nigar", "Due": today, "Status": "In Progress", "Notes": ""},
        {"Date": today, "Shift": "B", "Area": "Weld-Cell-A", "Priority": "P2", "Item": "Fixture bolts audit",
         "Owner": "Samir", "Due": today, "Status": "Open", "Notes": ""},
    ])

def _metrics(df: pd.DataFrame) -> dict:
    d = df.copy()
    d = _coerce_date(d, "Due")
    today = pd.Timestamp.utcnow().date()
    open_cnt = int((d["Status"] != "Done").sum())
    due_today = int(((d["Due"] == today) & (d["Status"] != "Done")).sum())
    overdue = int(((d["Due"] < today) & (d["Status"] != "Done")).sum())
    done_today = int(((d["Due"] == today) & (d["Status"] == "Done")).sum())
    return {"open": open_cnt, "due_today": due_today, "overdue": overdue, "done_today": done_today}

def render(T=None):
    if "huddle_df" not in st.session_state:
        st.session_state.huddle_df = _default_rows()

    st.title("🧭 Shift Huddle Board")
    st.caption("Daily stand-up: priorities, issues, owners, and timing.")

    with st.expander("Filters", expanded=False):
        c1, c2, c3 = st.columns([1,1,2])
        with c1: f_shift = st.multiselect("Shift", SHIFTS, default=SHIFTS)
        with c2: f_status = st.multiselect("Status", STATUS, default=STATUS)
        with c3: term = st.text_input("Search (Area/Item/Owner)", "")

    df = st.session_state.huddle_df.copy()
    df = _coerce_date(df, "Date")
    df = _coerce_date(df, "Due")

    mask = df["Shift"].isin(f_shift) & df["Status"].isin(f_status)
    if term.strip():
        q = term.lower()
        mask &= (df["Area"].str.lower().str.contains(q, na=False) |
                 df["Item"].str.lower().str.contains(q, na=False) |
                 df["Owner"].str.lower().str.contains(q, na=False))
    view = df.loc[mask].reset_index(drop=True)

    k = _metrics(df)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Open", k["open"]); k2.metric("Due Today", k["due_today"])
    k3.metric("Overdue", k["overdue"]); k4.metric("Completed Today", k["done_today"])

    st.divider()
    st.subheader("Huddle Items (edit inline)")
    edf = st.data_editor(
        view, num_rows="dynamic", use_container_width=True, key="huddle_editor",
        column_config={
            "Date": st.column_config.DateColumn(),
            "Shift": st.column_config.SelectboxColumn(options=SHIFTS),
            "Priority": st.column_config.SelectboxColumn(options=PRIORITY),
            "Status": st.column_config.SelectboxColumn(options=STATUS),
            "Due": st.column_config.DateColumn(),
        },
    )
    df.loc[mask, :] = edf.values
    st.session_state.huddle_df = df

    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "shift_huddle"

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("💾 Save", key="huddle_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": (st.session_state.huddle_df.assign(
                    Date=pd.to_datetime(st.session_state.huddle_df["Date"], errors="coerce").dt.date.astype(str),
                    Due=pd.to_datetime(st.session_state.huddle_df["Due"], errors="coerce").dt.date.astype(str),
                ).to_dict(orient="records")),
                "metrics": _metrics(st.session_state.huddle_df),
            }
            if save_project_doc: save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot: append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            # update consolidated snapshot
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")

    with c2:
        if st.button("📥 Load", key="huddle_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload: st.info("No saved Huddle data.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                df2 = _coerce_date(df2, "Date"); df2 = _coerce_date(df2, "Due")
                st.session_state.huddle_df = df2; st.success("Loaded Huddle data.")

    with c3:
        out = st.session_state.huddle_df.copy()
        for c in ("Date","Due"): out[c] = pd.to_datetime(out[c], errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "shift_huddle.csv", "text/csv")
