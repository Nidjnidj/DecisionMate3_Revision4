# workflows/tools/andon_log.py
from __future__ import annotations

import io
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Optional project persistence/history (graceful fallback if not present)
try:
    from data.firestore import load_project_doc, save_project_doc  # your app helpers
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
SEVERITY = ["Low", "Medium", "High", "Critical"]
CATEGORY = ["Equipment", "Material", "Quality", "Method", "Safety", "Other"]
STATUS = ["Open", "Containment", "Corrective", "In Verification", "Closed"]

# ---------- helpers ----------
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

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    ops_mode = st.session_state.get("ops_mode", "daily_ops")
    return f"{industry}:ops:{ops_mode}"

def _default_rows() -> pd.DataFrame:
    today = pd.Timestamp.utcnow().date()
    return pd.DataFrame([
        {"Date": today, "Line": "Press-1", "Station": "S-01", "Issue": "Die jam",
         "Severity": "High", "Downtime (min)": 18, "Category": "Equipment",
         "Root Cause": "Worn guide pin", "Countermeasure": "Replace pins",
         "Owner": "Ali", "Due": pd.NaT, "Status": "Corrective"},
        {"Date": today, "Line": "Assembly-1", "Station": "A-03", "Issue": "Missing fasteners",
         "Severity": "Medium", "Downtime (min)": 7, "Category": "Material",
         "Root Cause": "Kanban shortage", "Countermeasure": "Adjust min level",
         "Owner": "Leyla", "Due": pd.NaT, "Status": "Containment"},
        {"Date": today, "Line": "Weld-Cell-A", "Station": "W-02", "Issue": "Spatter / quality stop",
         "Severity": "Low", "Downtime (min)": 5, "Category": "Quality",
         "Root Cause": "Nozzle clog", "Countermeasure": "Standardize tip cleaning",
         "Owner": "Samir", "Due": pd.NaT, "Status": "Open"},
    ])

def _kpis(df: pd.DataFrame) -> dict:
    d = df.copy()
    d = _coerce_num(d, "Downtime (min)")
    total_inc = int(len(d))
    dt_sum = int(d["Downtime (min)"].sum())
    mttr = round(d["Downtime (min)"].mean(), 1) if total_inc > 0 else 0.0
    crit = int((d["Severity"] == "Critical").sum())
    open_cnt = int((d["Status"] != "Closed").sum())
    return {"incidents": total_inc, "downtime": dt_sum, "mttr": mttr, "critical": crit, "open": open_cnt}

def _bar_by_line(df: pd.DataFrame):
    d = _coerce_num(df.copy(), "Downtime (min)")
    by = d.groupby("Line", dropna=False)["Downtime (min)"].sum().sort_values(ascending=False)
    if by.empty:
        st.info("No data to chart yet.")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(by.index.astype(str), by.values)
    ax.set_title("Downtime by Line (minutes)")
    ax.set_ylabel("Minutes")
    ax.set_xticklabels(by.index.astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def _bar_by_cat(df: pd.DataFrame):
    d = _coerce_num(df.copy(), "Downtime (min)")
    by = d.groupby("Category", dropna=False)["Downtime (min)"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(by.index.astype(str), by.values)
    ax.set_title("Downtime by Category (minutes)")
    ax.set_ylabel("Minutes")
    ax.set_xticklabels(by.index.astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def _download(df: pd.DataFrame, name: str, label: str):
    out = df.copy()
    for c in ("Date", "Due"):
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.date.astype(str)
    st.download_button(label, out.to_csv(index=False).encode("utf-8"), name, "text/csv")

# ---------- UI ----------
def render(T=None):
    # init state
    if "andon_df" not in st.session_state:
        st.session_state.andon_df = _default_rows()

    st.title("🚨 Andon Incident Log")
    st.caption("Capture incidents, track downtime and root causes, and drive countermeasures.")

    # Filters
    with st.expander("Filters", expanded=False):
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            f_line = st.multiselect("Line", LINES, default=LINES)
        with c2:
            f_sev = st.multiselect("Severity", SEVERITY, default=SEVERITY)
        with c3:
            q = st.text_input("Search Issue/Root Cause/Owner", "")

    df = st.session_state.andon_df.copy()
    df = _coerce_date(df, "Date")
    df = _coerce_date(df, "Due")
    df = _coerce_num(df, "Downtime (min)")

    mask = df["Line"].isin(f_line) & df["Severity"].isin(f_sev)
    if q.strip():
        s = q.lower()
        mask &= (
            df["Issue"].str.lower().str.contains(s, na=False) |
            df["Root Cause"].str.lower().str.contains(s, na=False) |
            df["Owner"].str.lower().str.contains(s, na=False)
        )
    view = df.loc[mask].reset_index(drop=True)

    # KPIs
    k = _kpis(df)
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Incidents", k["incidents"])
    k2.metric("Downtime (min)", k["downtime"])
    k3.metric("MTTR (min/incident)", k["mttr"])
    k4.metric("Critical", k["critical"])
    k5.metric("Open", k["open"])

    st.divider()

    # Editor
    st.subheader("Incident Table (edit inline)")
    edf = st.data_editor(
        view,
        num_rows="dynamic",
        use_container_width=True,
        key="andon_editor",
        column_config={
            "Date": st.column_config.DateColumn(),
            "Line": st.column_config.SelectboxColumn(options=LINES),
            "Station": st.column_config.TextColumn(),
            "Issue": st.column_config.TextColumn(),
            "Severity": st.column_config.SelectboxColumn(options=SEVERITY),
            "Downtime (min)": st.column_config.NumberColumn(min_value=0, step=1),
            "Category": st.column_config.SelectboxColumn(options=CATEGORY),
            "Root Cause": st.column_config.TextColumn(),
            "Countermeasure": st.column_config.TextColumn(),
            "Owner": st.column_config.TextColumn(),
            "Due": st.column_config.DateColumn(),
            "Status": st.column_config.SelectboxColumn(options=STATUS),
        },
    )

    # merge back edits
    df.loc[mask, :] = edf.values
    st.session_state.andon_df = df

    st.divider()

    # Charts
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Downtime by Line")
        _bar_by_line(df)
    with c2:
        st.subheader("Downtime by Category")
        _bar_by_cat(df)

    st.divider()

    # Save/Load/Back/Export
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "andon_log"

    b1, b2, b3, b4 = st.columns([1,1,1,2])

    with b1:
        if st.button("💾 Save", key="andon_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": (st.session_state.andon_df.assign(
                    Date=pd.to_datetime(st.session_state.andon_df["Date"], errors="coerce").dt.date.astype(str),
                    Due=pd.to_datetime(st.session_state.andon_df["Due"], errors="coerce").dt.date.astype(str),
                ).to_dict(orient="records")),
                "kpis": _kpis(st.session_state.andon_df),
            }
            if save_project_doc:
                save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot:
                append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass

            st.success(f"Saved to [{namespace}] / {DOC_KEY}")
    with b2:
        if st.button("📥 Load", key="andon_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved Andon data found for this project/namespace.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                df2 = _coerce_date(df2, "Date")
                df2 = _coerce_date(df2, "Due")
                df2 = _coerce_num(df2, "Downtime (min)")
                st.session_state.andon_df = df2
                st.success("Loaded Andon data.")

    with b3:
        if st.button("↩ Back to Ops Hub", key="andon_back"):
            back_to_hub()

    with b4:
        _download(st.session_state.andon_df, "andon_log.csv", "Export CSV")

    # TXT one-pager
    if st.button("Generate one-pager (TXT)", key="andon_txt"):
        buf = io.StringIO()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        k = _kpis(st.session_state.andon_df)
        buf.write(f"Andon Incident Log — {namespace}\nGenerated: {now}\n\n")
        buf.write(f"Incidents: {k['incidents']} | Downtime: {k['downtime']} min | MTTR: {k['mttr']} min | Critical: {k['critical']} | Open: {k['open']}\n\n")
        for _, r in st.session_state.andon_df.sort_values("Downtime (min)", ascending=False).iterrows():
            buf.write(
                f"- {r['Date']} | {r['Line']} {r['Station']} | {r['Issue']} "
                f"({r['Severity']}/{r['Category']}) | DT: {int(r['Downtime (min)'])} | "
                f"RC: {r['Root Cause']} | CM: {r['Countermeasure']} | "
                f"Owner: {r['Owner']} | Due: {pd.to_datetime(r['Due']).date() if pd.notna(r['Due']) else '—'} | "
                f"Status: {r['Status']}\n"
            )
        st.download_button("Download one-pager (TXT)", buf.getvalue().encode("utf-8"), "andon_summary.txt", "text/plain")
