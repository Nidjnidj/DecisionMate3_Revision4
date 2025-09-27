# workflows/tools/cmms_lite.py
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

TYPE = ["PM", "CM"]
PRIORITY = ["P1", "P2", "P3"]
STATUS = ["Open", "In Progress", "Waiting Parts", "Done"]

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:daily_ops"

def _coerce_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns: df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df
def _coerce_num(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns: df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0); return df

def _default_rows() -> pd.DataFrame:
    today = pd.Timestamp.utcnow().date()
    return pd.DataFrame([
        {"WO": "WO-1001", "Type": "PM", "Priority": "P2", "Equipment": "Press-1",
         "Reported": today, "Due": today, "Completed": pd.NaT, "Est (min)": 60, "Act (min)": 0, "Status": "In Progress"},
        {"WO": "WO-1002", "Type": "CM", "Priority": "P1", "Equipment": "Weld-Cell-A",
         "Reported": today, "Due": today, "Completed": pd.NaT, "Est (min)": 45, "Act (min)": 0, "Status": "Open"},
    ])

def _metrics(df: pd.DataFrame) -> dict:
    d = df.copy()
    d = _coerce_date(d, "Due"); d = _coerce_date(d, "Completed")
    d = _coerce_num(d, "Act (min)")
    today = pd.Timestamp.utcnow().date()
    open_cnt = int((d["Status"] != "Done").sum())
    overdue = int(((d["Due"] < today) & (d["Status"] != "Done")).sum())
    done = int((d["Status"] == "Done").sum())
    act_sum = int(d["Act (min)"].sum())
    return {"open": open_cnt, "overdue": overdue, "done": done, "actual_min": act_sum}

def render(T=None):
    if "cmms_df" not in st.session_state:
        st.session_state.cmms_df = _default_rows()

    st.title("🛠️ CMMS (Lite) — Work Orders")
    st.caption("Track PM/CM orders, priorities, due/complete, and effort minutes.")

    with st.expander("Filters", expanded=False):
        c1, c2, c3 = st.columns([1,1,2])
        with c1: f_type = st.multiselect("Type", TYPE, default=TYPE)
        with c2: f_status = st.multiselect("Status", STATUS, default=STATUS)
        with c3: term = st.text_input("Search (WO/Equip/Owner)", "")

    df = st.session_state.cmms_df.copy()
    for c in ("Reported","Due","Completed"): df = _coerce_date(df, c)
    for c in ("Est (min)","Act (min)"): df = _coerce_num(df, c)

    mask = df["Type"].isin(f_type) & df["Status"].isin(f_status)
    if term.strip():
        q = term.lower()
        mask &= (df["WO"].str.lower().str.contains(q, na=False) |
                 df["Equipment"].str.lower().str.contains(q, na=False))
    view = df.loc[mask].reset_index(drop=True)

    k = _metrics(df)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Open", k["open"]); k2.metric("Overdue", k["overdue"])
    k3.metric("Completed", k["done"]); k4.metric("Effort (min)", k["actual_min"])

    st.divider()
    st.subheader("Work Orders (edit inline)")
    edf = st.data_editor(
        view, num_rows="dynamic", use_container_width=True, key="cmms_editor",
        column_config={
            "Type": st.column_config.SelectboxColumn(options=TYPE),
            "Priority": st.column_config.SelectboxColumn(options=PRIORITY),
            "Reported": st.column_config.DateColumn(),
            "Due": st.column_config.DateColumn(),
            "Completed": st.column_config.DateColumn(),
            "Est (min)": st.column_config.NumberColumn(min_value=0, step=5),
            "Act (min)": st.column_config.NumberColumn(min_value=0, step=5),
            "Status": st.column_config.SelectboxColumn(options=STATUS),
        },
    )
    df.loc[mask, :] = edf.values
    st.session_state.cmms_df = df

    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "cmms_lite"

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("💾 Save", key="cmms_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": (st.session_state.cmms_df.assign(
                    Reported=pd.to_datetime(st.session_state.cmms_df["Reported"], errors="coerce").dt.date.astype(str),
                    Due=pd.to_datetime(st.session_state.cmms_df["Due"], errors="coerce").dt.date.astype(str),
                    Completed=pd.to_datetime(st.session_state.cmms_df["Completed"], errors="coerce").dt.date.astype(str),
                ).to_dict(orient="records")),
                "metrics": _metrics(st.session_state.cmms_df),
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
        if st.button("📥 Load", key="cmms_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload: st.info("No saved CMMS data.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                for c in ("Reported","Due","Completed"): df2 = _coerce_date(df2, c)
                for c in ("Est (min)","Act (min)"): df2 = _coerce_num(df2, c)
                st.session_state.cmms_df = df2; st.success("Loaded CMMS data.")

    with c3:
        out = st.session_state.cmms_df.copy()
        for c in ("Reported","Due","Completed"): out[c] = pd.to_datetime(out[c], errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "cmms_workorders.csv", "text/csv")
