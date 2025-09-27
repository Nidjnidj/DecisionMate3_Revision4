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

STATUSES = ["Open","Mitigating","Accepted","Closed"]
def _coerce_date(df,col):
    if col not in df.columns: df[col]=pd.NaT
    df[col]=pd.to_datetime(df[col],errors="coerce").dt.date; return df
def _coerce_num(df,col):
    if col not in df.columns: df[col]=0
    df[col]=pd.to_numeric(df[col],errors="coerce").fillna(0); return df
def _namespace():
    industry = st.session_state.get("project_industry", st.session_state.get("industry","manufacturing"))
    return f"{industry}:ops:small_projects"
def _default():
    return pd.DataFrame([
        {"Risk":"Supplier delay","Category":"Supply","Likelihood (1-5)":3,"Impact (1-5)":3,"Exposure":9,"Owner":"","Due":pd.NaT,"Status":"Open","Notes":""},
        {"Risk":"Equipment breakdown","Category":"Equipment","Likelihood (1-5)":2,"Impact (1-5)":5,"Exposure":10,"Owner":"","Due":pd.NaT,"Status":"Open","Notes":""},
    ])

def _recalc(df):
    d=df.copy()
    d=_coerce_num(d,"Likelihood (1-5)"); d=_coerce_num(d,"Impact (1-5)")
    d["Exposure"] = (d["Likelihood (1-5)"]*d["Impact (1-5)"]).astype(int)
    return d

def _scatter(df):
    d=_recalc(df)
    if d.empty: st.info("Add risks to chart."); return
    fig,ax=plt.subplots(figsize=(6,5))
    ax.scatter(d["Likelihood (1-5)"], d["Impact (1-5)"], s=(d["Exposure"]*20))
    ax.set_xlabel("Likelihood"); ax.set_ylabel("Impact"); ax.set_title("Risk Matrix (bubble size = exposure)")
    ax.set_xticks([1,2,3,4,5]); ax.set_yticks([1,2,3,4,5])
    st.pyplot(fig)

def render(T=None):
    if "risk_df" not in st.session_state: st.session_state.risk_df=_default()
    st.title("⚠️ Risk (Lite)")
    st.caption("Simple risk register with exposure and a bubble matrix.")
    df=st.session_state.risk_df.copy()
    df=_coerce_date(df,"Due"); df=_coerce_num(df,"Likelihood (1-5)"); df=_coerce_num(df,"Impact (1-5)")
    edf=st.data_editor(
        df,num_rows="dynamic",use_container_width=True,key="risk_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn(options=STATUSES),
            "Due": st.column_config.DateColumn(),
            "Likelihood (1-5)": st.column_config.NumberColumn(min_value=1,max_value=5,step=1),
            "Impact (1-5)": st.column_config.NumberColumn(min_value=1,max_value=5,step=1),
        }
    )
    edf=_recalc(edf); st.session_state.risk_df=edf

    st.divider(); st.subheader("Matrix")
    _scatter(edf)

    st.divider(); st.subheader("Save / Load / Export")
    namespace=_namespace(); username=st.session_state.get("username","Guest")
    project_id=st.session_state.get("active_project_id") or "P-DEMO"; DOC_KEY="risk_lite"
    c1,c2,c3,c4=st.columns([1,1,1,2])
    with c1:
        if st.button("💾 Save", key="risk_save"):
            payload={"meta":{"saved_at": datetime.utcnow().isoformat()},
                     "rows": edf.assign(
                        Due=pd.to_datetime(edf["Due"],errors="coerce").dt.date.astype(str)
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
        if st.button("📥 Load", key="risk_load"):
            payload=load_project_doc(username,namespace,project_id,DOC_KEY) if load_project_doc else None
            if not payload: st.info("No saved data.")
            else:
                df2=pd.DataFrame(payload.get("rows",[]))
                df2=_coerce_date(df2,"Due"); df2=_coerce_num(df2,"Likelihood (1-5)"); df2=_coerce_num(df2,"Impact (1-5)")
                df2=_recalc(df2); st.session_state.risk_df=df2; st.success("Loaded.")
    with c3:
        if st.button("↩ Back", key="risk_back"): back_to_hub()
    with c4:
        out=edf.copy(); out["Due"]=pd.to_datetime(out["Due"],errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "risk_lite.csv", "text/csv")
