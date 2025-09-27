from __future__ import annotations
import io
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

STATUSES = ["Planned", "In Progress", "Blocked", "Done"]
EFFORTS = ["Low", "Medium", "High"]

def _coerce_date(df, col):
    if col not in df.columns: df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df
def _coerce_num(df, col):
    if col not in df.columns: df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0); return df
def _namespace():
    industry = st.session_state.get("project_industry", st.session_state.get("industry","manufacturing"))
    return f"{industry}:ops:small_projects"
def _default():
    return pd.DataFrame([
        {"WBS": "1.0", "Deliverable/Task": "Scope & requirements", "Owner": "", "Effort": "Low",
         "Start": pd.NaT, "Finish": pd.NaT, "Predecessors": "", "Status": "Planned"},
        {"WBS": "2.0", "Deliverable/Task": "Design / method", "Owner": "", "Effort": "Medium",
         "Start": pd.NaT, "Finish": pd.NaT, "Predecessors": "1.0", "Status": "Planned"},
        {"WBS": "3.0", "Deliverable/Task": "Implement", "Owner": "", "Effort": "High",
         "Start": pd.NaT, "Finish": pd.NaT, "Predecessors": "2.0", "Status": "Planned"},
    ])

def _gantt(df: pd.DataFrame):
    d = df.copy()
    d = _coerce_date(d, "Start"); d = _coerce_date(d, "Finish")
    d = d.dropna(subset=["Start","Finish"])
    if d.empty:
        st.info("Add Start/Finish dates to show a timeline.")
        return
    d["StartNum"]  = pd.to_datetime(d["Start"]).map(pd.Timestamp.toordinal)
    d["FinishNum"] = pd.to_datetime(d["Finish"]).map(pd.Timestamp.toordinal)
    d["Dur"] = d["FinishNum"] - d["StartNum"]
    d = d.sort_values("StartNum")
    fig, ax = plt.subplots(figsize=(8,4))
    ax.barh(d["Deliverable/Task"], d["Dur"], left=d["StartNum"])
    ax.set_title("Schedule (Gantt-like)"); ax.set_xlabel("Date"); ax.invert_yaxis()
    # simple labeled ticks
    ticks = sorted(set(d["StartNum"].tolist()+d["FinishNum"].tolist()))
    ax.set_xticks(ticks); ax.set_xticklabels([pd.Timestamp.fromordinal(t).date() for t in ticks], rotation=45, ha="right")
    st.pyplot(fig)

def render(T=None):
    if "msb_df" not in st.session_state: st.session_state.msb_df = _default()

    st.title("📝 Mini Scope Builder")
    st.caption("Define WBS / tasks for small projects with dates and simple timeline.")

    df = st.session_state.msb_df.copy()
    df = _coerce_date(df, "Start"); df = _coerce_date(df, "Finish")

    edf = st.data_editor(
        df, num_rows="dynamic", use_container_width=True, key="msb_editor",
        column_config={
            "Effort": st.column_config.SelectboxColumn(options=EFFORTS),
            "Status": st.column_config.SelectboxColumn(options=STATUSES),
            "Start": st.column_config.DateColumn(),
            "Finish": st.column_config.DateColumn(),
        },
    )
    st.session_state.msb_df = edf

    st.divider()
    st.subheader("Timeline")
    _gantt(edf)

    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace(); username = st.session_state.get("username","Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"; DOC_KEY = "mini_scope_builder"

    c1,c2,c3,c4 = st.columns([1,1,1,2])
    with c1:
        if st.button("💾 Save", key="msb_save"):
            payload = {"meta":{"saved_at": datetime.utcnow().isoformat()},
                       "rows": edf.assign(
                           Start=pd.to_datetime(edf["Start"],errors="coerce").dt.date.astype(str),
                           Finish=pd.to_datetime(edf["Finish"],errors="coerce").dt.date.astype(str)
                       ).to_dict(orient="records")}
            if save_project_doc: save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot:  append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")
    with c2:
        if st.button("📥 Load", key="msb_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload: st.info("No saved data."); 
            else:
                df2 = pd.DataFrame(payload.get("rows",[]))
                df2 = _coerce_date(df2,"Start"); df2=_coerce_date(df2,"Finish")
                st.session_state.msb_df = df2; st.success("Loaded.")
    with c3:
        if st.button("↩ Back", key="msb_back"): back_to_hub()
    with c4:
        out = edf.copy()
        out["Start"]=pd.to_datetime(out["Start"],errors="coerce").dt.date.astype(str)
        out["Finish"]=pd.to_datetime(out["Finish"],errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "mini_scope.csv", "text/csv")
