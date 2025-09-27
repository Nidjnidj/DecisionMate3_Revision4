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

PHASES = ["Plan","Build","Trial","Handover","Done"]

def _coerce_date(df, col):
    if col not in df.columns: df[col]=pd.NaT
    df[col]=pd.to_datetime(df[col],errors="coerce").dt.date; return df
def _namespace():
    industry = st.session_state.get("project_industry", st.session_state.get("industry","manufacturing"))
    return f"{industry}:ops:small_projects"
def _default():
    return pd.DataFrame([
        {"Task":"Kickoff","Phase":"Plan","Start":pd.NaT,"Finish":pd.NaT,"Owner":"","Notes":""},
        {"Task":"Procure items","Phase":"Build","Start":pd.NaT,"Finish":pd.NaT,"Owner":"","Notes":""},
        {"Task":"Trial on line","Phase":"Trial","Start":pd.NaT,"Finish":pd.NaT,"Owner":"","Notes":""},
    ])

def _timeline(df):
    d=df.copy(); d=_coerce_date(d,"Start"); d=_coerce_date(d,"Finish"); d=d.dropna(subset=["Start","Finish"])
    if d.empty: st.info("Add Start/Finish to show timeline."); return
    d["StartNum"]=pd.to_datetime(d["Start"]).map(pd.Timestamp.toordinal)
    d["FinishNum"]=pd.to_datetime(d["Finish"]).map(pd.Timestamp.toordinal)
    d["Dur"]=d["FinishNum"]-d["StartNum"]; d=d.sort_values("StartNum")
    fig,ax=plt.subplots(figsize=(8,4))
    ax.barh(d["Task"], d["Dur"], left=d["StartNum"]); ax.set_title("Lightweight Schedule")
    ticks=sorted(set(d["StartNum"].tolist()+d["FinishNum"].tolist()))
    ax.set_xticks(ticks); ax.set_xticklabels([pd.Timestamp.fromordinal(t).date() for t in ticks], rotation=45, ha="right")
    ax.invert_yaxis(); st.pyplot(fig)

def render(T=None):
    if "lws_df" not in st.session_state: st.session_state.lws_df=_default()
    st.title("🗓️ Lightweight Schedule")
    st.caption("Simple schedule with phases and timeline for small jobs.")
    df=st.session_state.lws_df.copy(); df=_coerce_date(df,"Start"); df=_coerce_date(df,"Finish")
    edf=st.data_editor(
        df,num_rows="dynamic",use_container_width=True,key="lws_editor",
        column_config={
            "Phase": st.column_config.SelectboxColumn(options=PHASES),
            "Start": st.column_config.DateColumn(),
            "Finish": st.column_config.DateColumn(),
        }
    )
    st.session_state.lws_df=edf
    st.divider(); _timeline(edf)
    st.divider()
    st.subheader("Save / Load / Export")
    namespace=_namespace(); username=st.session_state.get("username","Guest")
    project_id=st.session_state.get("active_project_id") or "P-DEMO"; DOC_KEY="lightweight_schedule"
    c1,c2,c3,c4=st.columns([1,1,1,2])
    with c1:
        if st.button("💾 Save", key="lws_save"):
            payload={"meta":{"saved_at":datetime.utcnow().isoformat()},
                     "rows": edf.assign(
                        Start=pd.to_datetime(edf["Start"],errors="coerce").dt.date.astype(str),
                        Finish=pd.to_datetime(edf["Finish"],errors="coerce").dt.date.astype(str)
                     ).to_dict(orient="records")}
            if save_project_doc: save_project_doc(username,namespace,project_id,DOC_KEY,payload)
            if append_snapshot:  append_snapshot(username,namespace,project_id,DOC_KEY,payload)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")
    with c2:
        if st.button("📥 Load", key="lws_load"):
            payload=load_project_doc(username,namespace,project_id,DOC_KEY) if load_project_doc else None
            if not payload: st.info("No saved data.")
            else:
                df2=pd.DataFrame(payload.get("rows",[]))
                df2=_coerce_date(df2,"Start"); df2=_coerce_date(df2,"Finish")
                st.session_state.lws_df=df2; st.success("Loaded.")
    with c3:
        if st.button("↩ Back", key="lws_back"): back_to_hub()
    with c4:
        out=edf.copy()
        out["Start"]=pd.to_datetime(out["Start"],errors="coerce").dt.date.astype(str)
        out["Finish"]=pd.to_datetime(out["Finish"],errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "lightweight_schedule.csv", "text/csv")
