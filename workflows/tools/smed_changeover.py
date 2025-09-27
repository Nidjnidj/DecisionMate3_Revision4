# workflows/tools/smed_changeover.py
from __future__ import annotations
from services.kaizen_inbox import push_suggestions

import io
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from data.firestore import load_project_doc, save_project_doc  # persistence
from services.history import append_snapshot                   # run history
from services.utils import back_to_hub                         # optional: back button
import uuid
ECRS_CHOICES = ["—", "Eliminate", "Combine", "Rearrange (Ext)", "Simplify"]

# ---------------------------
# Utilities
# ---------------------------
def _coerce_date_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Ensure a column contains real date objects (not strings)."""
    if col not in df.columns:
        df[col] = pd.NaT
    # Convert to pandas datetime then to Python date objects
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def _fmt_date(x):
    try:
        return x.isoformat() if x else ""
    except Exception:
        return ""

def _kpis(df: pd.DataFrame):
    d = df.copy()
    d["Duration (min)"] = pd.to_numeric(d["Duration (min)"], errors="coerce").fillna(0)
    total = float(d["Duration (min)"].sum())
    internal = float(d.loc[d["Type"].str.lower() == "internal", "Duration (min)"].sum())
    external = float(d.loc[d["Type"].str.lower() == "external", "Duration (min)"].sum())
    return int(total), int(internal), int(external)

def _pareto_chart(df: pd.DataFrame):
    d = df.copy()

    # Coerce columns safely
    d["Duration (min)"] = pd.to_numeric(d.get("Duration (min)"), errors="coerce").fillna(0)
    # Ensure all x labels are strings (no None)
    d["Activity"] = d.get("Activity", pd.Series([], dtype="object"))
    d["Activity"] = d["Activity"].fillna("(blank)").astype(str)

    # Order by duration
    d = d.sort_values("Duration (min)", ascending=False)

    # Plot using integer positions to avoid category converter issues
    x = list(range(len(d)))
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(x, d["Duration (min)"])
    ax.set_title("Changeover Task Pareto (minutes)")
    ax.set_ylabel("Minutes")
    ax.set_xlabel("Activity")
    ax.set_xticks(x)
    ax.set_xticklabels(d["Activity"], rotation=45, ha="right")
    st.pyplot(fig)


def _suggest_conversions(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["Duration (min)"] = pd.to_numeric(d["Duration (min)"], errors="coerce").fillna(0)
    mask = (d["Type"].str.lower() == "internal") & (d["ECRS"].fillna("").str.startswith("Rearrange"))
    cand = d.loc[mask, ["Activity", "Duration (min)", "Owner", "Due"]].copy()
    if cand.empty:
        return cand
    cand.rename(columns={"Duration (min)": "Time Saved (min) (est.)"}, inplace=True)
    cand["Proposed Change"] = "Convert to External prep"
    return cand

def _download_df_button(df: pd.DataFrame, filename: str, label: str):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")
def _namespace() -> str:
    """Builds the same namespace your app uses: '<industry>:ops:<ops_mode>'."""
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    ops_mode = st.session_state.get("ops_mode", "daily_ops")
    return f"{industry}:ops:{ops_mode}"

# ---------------------------
# Init defaults (with DATE, not string)
# ---------------------------
def _init_state():
    if "smed_product" not in st.session_state:
        st.session_state.smed_product = "Press Line #3 — Bracket A"

    if "smed_tasks" not in st.session_state:
        st.session_state.smed_tasks = pd.DataFrame(
            [
                {"Activity": "Bring tools to line",       "Type": "External", "Duration (min)": 6,  "ECRS": "Combine",         "Owner": "", "Due": pd.NaT},
                {"Activity": "Remove old die",            "Type": "Internal", "Duration (min)": 10, "ECRS": "Simplify",        "Owner": "", "Due": pd.NaT},
                {"Activity": "Clean/inspect mounting",    "Type": "Internal", "Duration (min)": 8,  "ECRS": "Rearrange (Ext)", "Owner": "", "Due": pd.NaT},
                {"Activity": "Install new die",           "Type": "Internal", "Duration (min)": 12, "ECRS": "Simplify",        "Owner": "", "Due": pd.NaT},
                {"Activity": "Center/adjust & trial run", "Type": "Internal", "Duration (min)": 14, "ECRS": "—",               "Owner": "", "Due": pd.NaT},
                {"Activity": "Return old die to storage", "Type": "External", "Duration (min)": 5,  "ECRS": "Combine",         "Owner": "", "Due": pd.NaT},
            ]
        )

    if "smed_actions" not in st.session_state:
        st.session_state.smed_actions = pd.DataFrame(
            [
                {"Action": "5S tooling carts & shadow boards", "Owner": "", "Due": pd.NaT, "Status": "Planned"},
                {"Action": "Pre-set fasteners offline",         "Owner": "", "Due": pd.NaT, "Status": "Planned"},
            ]
        )
def _ensure_ids_and_promote(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee each row has a stable ID and a Promote flag."""
    if "ID" not in df.columns:
        df["ID"] = ""
    df["ID"] = df["ID"].apply(lambda x: x if isinstance(x, str) and x else uuid.uuid4().hex)
    if "Promote" not in df.columns:
        df["Promote"] = False
    return df

# ---------------------------
# Public entry
# ---------------------------
def render(T=None):
    _init_state()

    st.title("⏱️ SMED Changeover Reduction")
    st.caption("Structure changeover into Internal vs External steps, apply ECRS, and drive an action plan.")

    # ---- Context
    with st.expander("Context", expanded=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.session_state.smed_product = st.text_input("Line / Product", value=st.session_state.smed_product)
        with c2:
            current = st.number_input("Current changeover (min)", value=55, min_value=0, step=1, key="smed_current")
        with c3:
            target = st.number_input("Target (min)", value=30, min_value=0, step=1, key="smed_target")
        gap = max(0, current - target)
        st.metric("Gap to eliminate (min)", gap)

    # ---- Activities (editable)  — coerce date column BEFORE sending to editor
    st.subheader("Activities (edit inline)")
    tasks = _coerce_date_col(st.session_state.smed_tasks.copy(), "Due")
    tasks = _ensure_ids_and_promote(tasks)                      # ⬅️ add
    task_df: pd.DataFrame = st.data_editor(
        tasks,
        num_rows="dynamic",
        use_container_width=True,
        key="smed_editor",
        column_config={
            "Type": st.column_config.SelectboxColumn(options=["Internal", "External"]),
            "ECRS": st.column_config.SelectboxColumn(options=ECRS_CHOICES),
            "Duration (min)": st.column_config.NumberColumn(min_value=0, step=1),
            "Due": st.column_config.DateColumn(),
            "Promote": st.column_config.CheckboxColumn(               # ⬅️ add
                help="Tick to send this row to the Kaizen inbox on Save"
            ),
            "ID": st.column_config.TextColumn(disabled=True),         # ⬅️ add
        },
    )
    st.session_state.smed_tasks = _ensure_ids_and_promote(       # ⬅️ add
        _coerce_date_col(task_df, "Due")
    )


    total, internal, external = _kpis(task_df)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Changeover (min)", total)
    k2.metric("Internal (min)", internal)
    k3.metric("External (min)", external)
    k4.metric("Potential gain (min)", max(0, internal - external))

    st.divider()

    # ---- Pareto
    st.subheader("Pareto of Task Durations")
    if not task_df.empty:
        _pareto_chart(task_df)
    else:
        st.info("Add tasks above to see the Pareto chart.")

    st.divider()

    # ---- Suggestions
    st.subheader("Conversion Candidates & ECRS Actions")
    suggestions = _suggest_conversions(task_df)
    if suggestions.empty:
        st.info("No Internal tasks marked as 'Rearrange (Ext)'. Tag candidates in the ECRS column to populate suggestions.")
    else:
        st.dataframe(suggestions, use_container_width=True)
    # --- Quick KPI: estimated time saved if candidates are converted
    saved_est = 0
    if not suggestions.empty and "Time Saved (min) (est.)" in suggestions.columns:
        saved_est = int(pd.to_numeric(suggestions["Time Saved (min) (est.)"], errors="coerce").fillna(0).sum())
    new_est = max(0, current - saved_est)
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Estimated time saved (min)", saved_est)
    kpi2.metric("New changeover (est.)", new_est)

    # ---- Action Plan (editable) — coerce date column BEFORE editor
    st.subheader("Action Plan")
    actions = _coerce_date_col(st.session_state.smed_actions.copy(), "Due")
    action_df: pd.DataFrame = st.data_editor(
        actions,
        num_rows="dynamic",
        use_container_width=True,
        key="smed_actions_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn(options=["Planned", "In Progress", "Blocked", "Done"]),
            "Due": st.column_config.DateColumn(),
        },
    )
    st.session_state.smed_actions = _coerce_date_col(action_df, "Due")
    # ---- Persist to project (Save / Load)
    st.subheader("Save / Load")
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    namespace  = _namespace()
    DOC_KEY    = "smed_changeover"  # single doc that stores the latest state

    c_s, c_l, c_b = st.columns([1,1,1])

    with c_s:
        if st.button("💾 Save to Project", key="smed_save"):
            payload = {
                "meta": {
                    "product": st.session_state.smed_product,
                    "current_min": int(st.session_state.get("smed_current", 55)),
                    "target_min": int(st.session_state.get("smed_target", 30)),
                },
                "totals": {
                    "total": int(total),
                    "internal": int(internal),
                    "external": int(external),
                    "saved_est": int(saved_est),
                    "new_changeover_est": int(new_est),
                },
                # convert dates to ISO strings to be safe in Firestore/JSON
                "tasks": (st.session_state.smed_tasks.assign(
                    Due=pd.to_datetime(st.session_state.smed_tasks["Due"], errors="coerce").dt.date.astype(str)
                ).to_dict(orient="records")),
                "actions": (st.session_state.smed_actions.assign(
                    Due=pd.to_datetime(st.session_state.smed_actions["Due"], errors="coerce").dt.date.astype(str)
                ).to_dict(orient="records")),
            }
            save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")
# --- Also send any rows with Promote == True to the Kaizen inbox
            try:
                rows = st.session_state.smed_tasks.copy()
                rows = _ensure_ids_and_promote(rows)

                to_send = rows[rows["Promote"] == True]
                ideas = []
                for _, r in to_send.iterrows():
                    # Prefer “Time Saved (min) (est.)” if it exists; fallback to Duration
                    benefit = pd.to_numeric(
                        r.get("Time Saved (min) (est.)", r.get("Duration (min)", 0)),
                        errors="coerce"
                    )
                    benefit = 0 if pd.isna(benefit) else int(benefit)

                    ideas.append({
                        "uid": f"smed:{r['ID']}",
                        "source": "SMED",
                        "title": f"Reduce changeover — {r.get('Activity','')}",
                        "area": st.session_state.get("smed_product", ""),
                        "owner": r.get("Owner",""),
                        "due": _fmt_date(r.get("Due")),
                        "benefit": benefit,
                        "notes": f"ECRS: {r.get('ECRS','')}; Type: {r.get('Type','')}",
                    })

                if ideas:
                    added = push_suggestions(username, namespace, project_id, ideas)
                    if added:
                        st.success(f"Sent {added} task(s) to Kaizen inbox.")
            except Exception as e:
                st.warning(f"Could not push to Kaizen inbox: {e}")

    with c_l:
        if st.button("📥 Load last saved", key="smed_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY)
            if not payload:
                st.info("No saved SMED data found for this project/namespace.")
            else:
                # restore tables + fields; coerce dates back to date objects
                st.session_state.smed_product = payload.get("meta", {}).get("product", st.session_state.smed_product)

                tdf = pd.DataFrame(payload.get("tasks", []))
                if "Due" in tdf.columns:
                    tdf["Due"] = pd.to_datetime(tdf["Due"], errors="coerce").dt.date
                st.session_state.smed_tasks = tdf

                adf = pd.DataFrame(payload.get("actions", []))
                if "Due" in adf.columns:
                    adf["Due"] = pd.to_datetime(adf["Due"], errors="coerce").dt.date
                st.session_state.smed_actions = adf

                st.success("Loaded last saved SMED state.")

    with c_b:
        if st.button("↩ Back to Ops Hub", key="smed_back"):
            back_to_hub()

    # ---- Exports
    st.divider()
    e1, e2, e3 = st.columns([1, 1, 2])
    with e1:
        _download_df_button(st.session_state.smed_tasks, "smed_changeover_tasks.csv", "Download tasks (CSV)")
    with e2:
        _download_df_button(st.session_state.smed_actions, "smed_action_plan.csv", "Download action plan (CSV)")
    with e3:
        if st.button("Generate one-pager (TXT)"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            buf = io.StringIO()
            buf.write(f"SMED Changeover Reduction — {st.session_state.smed_product}\nGenerated: {now}\n\n")
            buf.write(f"Current: {current} min  |  Target: {target} min  |  Gap: {gap} min\n")
            buf.write(f"Totals -> Internal: {internal} min | External: {external} min | Total: {total} min\n\n")
            buf.write("Top Tasks (by duration):\n")
            for _, row in st.session_state.smed_tasks.sort_values("Duration (min)", ascending=False).head(10).iterrows():
                buf.write(f" - {row['Activity']} [{row['Type']}]: {row['Duration (min)']} min | ECRS: {row['ECRS']}\n")
            buf.write("\nAction Plan:\n")
            for _, row in st.session_state.smed_actions.iterrows():
                buf.write(f" - {row['Action']} | Owner: {row['Owner']} | Due: {_fmt_date(row['Due'])} | Status: {row['Status']}\n")
            st.download_button(
                "Download one-pager (TXT)",
                data=buf.getvalue().encode("utf-8"),
                file_name="smed_one_pager.txt",
                mime="text/plain",
            )
