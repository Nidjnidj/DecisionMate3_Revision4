# workflows/tools/kaizen_tracker.py
from __future__ import annotations

import io
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# …
from services.kaizen_inbox import list_suggestions, delete_suggestions

# ==== (Optional) project persistence / history ====
try:
    from data.firestore import load_project_doc, save_project_doc  # your app's helpers
except Exception:
    load_project_doc = save_project_doc = None  # graceful fallback

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

# ---------------------------
# Constants & helpers
# ---------------------------
AREAS = ["Press Shop", "Welding", "Assembly", "Paint", "Logistics", "QA", "Maintenance"]
TYPES = ["Quality", "Delivery", "Cost", "Safety", "Morale"]
STATUSES = ["Idea", "Screening", "Trial", "Standardize", "Done", "Drop"]
EFFORTS = ["Low", "Medium", "High"]
DEFAULT_WIP_LIMIT = 5  # for Trial column

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
    ops_mode = st.session_state.get("ops_mode", "small_projects")
    return f"{industry}:ops:{ops_mode}"

def _default_ideas() -> pd.DataFrame:
    # include an immutable ID column for safe updates & board buttons
    return pd.DataFrame([
        {"ID": 1, "Idea": "Shadow board for changeover tools",
         "Area": "Press Shop", "Type": "Delivery", "Status": "Screening",
         "Effort": "Low", "Monthly Benefit": 800, "One-off Cost": 150,
         "Start": pd.NaT, "Due": pd.NaT, "Owner": "", "Notes": "Reduce search time"},
        {"ID": 2, "Idea": "Kanban for consumables",
         "Area": "Assembly", "Type": "Delivery", "Status": "Trial",
         "Effort": "Medium", "Monthly Benefit": 500, "One-off Cost": 200,
         "Start": pd.NaT, "Due": pd.NaT, "Owner": "", "Notes": ""},
        {"ID": 3, "Idea": "Poka-Yoke fixture for misload",
         "Area": "Welding", "Type": "Quality", "Status": "Idea",
         "Effort": "High", "Monthly Benefit": 1200, "One-off Cost": 3000,
         "Start": pd.NaT, "Due": pd.NaT, "Owner": "", "Notes": "Needs design"},
    ])

def _ensure_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Guarantee an 'ID' column with stable integers."""
    if "ID" not in df.columns:
        df = df.copy()
        # assign new IDs incrementally
        df["ID"] = range(1, len(df) + 1)
    else:
        # fill any missing/duplicate gracefully
        if df["ID"].isnull().any() or df["ID"].duplicated().any():
            base = 1
            used = set()
            new_ids = []
            for x in df["ID"]:
                if pd.isna(x) or x in used:
                    while base in used:
                        base += 1
                    new_ids.append(base)
                    used.add(base)
                else:
                    new_ids.append(int(x))
                    used.add(int(x))
            df = df.copy()
            df["ID"] = new_ids
    return df

def _portfolio_metrics(df: pd.DataFrame) -> dict:
    d = df.copy()
    d = _coerce_num(d, "Monthly Benefit")
    d = _coerce_num(d, "One-off Cost")

    monthly_total = int(d["Monthly Benefit"].sum())
    oneoff_total = int(d["One-off Cost"].sum())

    payback = round(oneoff_total / monthly_total, 1) if monthly_total > 0 else None
    roi_annual = None
    if oneoff_total > 0:
        roi_annual = round(((12 * monthly_total - oneoff_total) / oneoff_total) * 100, 1)

    counts = {s: int((d["Status"] == s).sum()) for s in STATUSES}
    return {
        "monthly_total": monthly_total,
        "oneoff_total": oneoff_total,
        "payback": payback,
        "roi_annual": roi_annual,
        "counts": counts,
    }

def _pareto(df: pd.DataFrame):
    d = _coerce_num(df.copy(), "Monthly Benefit")
    d = d.sort_values("Monthly Benefit", ascending=False).head(10)
    if d.empty:
        st.info("Add ideas with a positive Monthly Benefit to see the Pareto.")
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(d["Idea"], d["Monthly Benefit"])
    ax.set_title("Top ideas by Monthly Benefit (Pareto)")
    ax.set_ylabel("Benefit per month")
    ax.set_xticklabels(d["Idea"], rotation=45, ha="right")
    st.pyplot(fig)

def _download(df: pd.DataFrame, name: str, label: str):
    df_out = df.copy()
    for c in ("Start", "Due"):
        if c in df_out.columns:
            df_out[c] = pd.to_datetime(df_out[c], errors="coerce").dt.date.astype(str)
    st.download_button(label, df_out.to_csv(index=False).encode("utf-8"), name, "text/csv")

def _next_status(s: str) -> str | None:
    try:
        i = STATUSES.index(s)
        return STATUSES[i + 1] if i + 1 < len(STATUSES) else None
    except ValueError:
        return None

def _prev_status(s: str) -> str | None:
    try:
        i = STATUSES.index(s)
        return STATUSES[i - 1] if i - 1 >= 0 else None
    except ValueError:
        return None

# ---------------------------
# Public entry
# ---------------------------
def render(T=None):
    # init state
    if "kaizen_df" not in st.session_state:
        st.session_state.kaizen_df = _default_ideas()
    st.session_state.kaizen_df = _ensure_ids(st.session_state.kaizen_df)

    if "kaizen_wip_limit" not in st.session_state:
        st.session_state.kaizen_wip_limit = DEFAULT_WIP_LIMIT

    st.title("🧩 Kaizen Tracker")
    st.caption("Capture ideas → screen → trial → standardize, and track ROI/payback. Includes WIP limit & a swimlane board.")

    # ---- Filters / settings
    with st.expander("Filters & Board Settings", expanded=False):
        c1, c2, c3, c4 = st.columns([1,1,2,2])
        with c1:
            f_status = st.multiselect("Status", STATUSES, default=STATUSES, key="kaizen_filter_status")
        with c2:
            f_type = st.multiselect("Type", TYPES, default=TYPES, key="kaizen_filter_type")
        with c3:
            query = st.text_input("Search (Idea/Area/Owner/Notes)", value="", key="kaizen_search")
        with c4:
            st.session_state.kaizen_wip_limit = st.number_input(
                "WIP limit for Trial", min_value=1, max_value=50,
                value=st.session_state.kaizen_wip_limit, step=1, key="kaizen_wip_limit_input"
            )

    data = st.session_state.kaizen_df.copy()
    data = _coerce_date(data, "Start")
    data = _coerce_date(data, "Due")
    data = _coerce_num(data, "Monthly Benefit")
    data = _coerce_num(data, "One-off Cost")

    # apply filters
    mask = data["Status"].isin(f_status) & data["Type"].isin(f_type)
    if query.strip():
        q = query.lower()
        mask &= (
            data["Idea"].str.lower().str.contains(q, na=False) |
            data["Area"].str.lower().str.contains(q, na=False) |
            data["Owner"].str.lower().str.contains(q, na=False) |
            data["Notes"].str.lower().str.contains(q, na=False)
        )
    data_f = data.loc[mask].reset_index(drop=True)

    # ---- Portfolio KPIs & WIP indicator
    m = _portfolio_metrics(data)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Ideas", len(data))
    k2.metric("In Trial", m["counts"].get("Trial", 0))
    k3.metric("Standardized", m["counts"].get("Standardize", 0))
    k4.metric("Monthly Benefit (sum)", m["monthly_total"])
    k5.metric("One-off Cost (sum)", m["oneoff_total"])
    k6.metric("Payback (months)", m["payback"] if m["payback"] is not None else "—")

    if m["roi_annual"] is not None:
        st.metric("Annual ROI (%)", m["roi_annual"])

    # WIP limit warning row (Trial column)
    trial_now = m["counts"].get("Trial", 0)
    limit = int(st.session_state.kaizen_wip_limit)
    if trial_now > limit:
        st.error(f"Trial WIP limit exceeded: {trial_now} / {limit}")
    else:
        st.caption(f"Trial WIP: {trial_now} / {limit}")

    # ---- Inbox from other tools (SMED, Andon, etc.)
    namespace  = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"

    inbox = []  # ensure it's defined even if list_suggestions fails
    try:
        inbox = list_suggestions(username, namespace, project_id)
    except Exception:
        pass

    with st.expander("Inbox — suggestions from other tools", expanded=False):
        if not inbox:
            st.caption("No suggestions waiting.")
        else:
            df_in = pd.DataFrame(inbox)
            if "Import" not in df_in.columns:
                df_in["Import"] = True

            cols = [c for c in ["Import","source","title","area","owner","due","benefit","notes","uid"]
                    if c in df_in.columns]
            view = st.data_editor(
                df_in[cols],
                use_container_width=True,
                key="kaizen_inbox_editor",
            )

            if st.button("Import selected", key="kaizen_inbox_import"):
                to_take = view[view.get("Import", False) == True] if "Import" in view.columns else view

                new_rows = []
                for _, r in to_take.iterrows():
                    new_rows.append({
                        "Idea": r.get("title",""),
                        "Area": r.get("area",""),
                        "Type": "Delivery",
                        "Status": "Screening",
                        "Effort": "Medium",
                        "Monthly Benefit": int(pd.to_numeric(r.get("benefit", 0), errors="coerce") or 0),
                        "One-off Cost": 0,
                        "Start": pd.NaT,
                        "Due": pd.to_datetime(r.get("due"), errors="coerce").date() if r.get("due") else pd.NaT,
                        "Owner": r.get("owner",""),
                        "Notes": f"[From {r.get('source','')}] {r.get('notes','')}",
                    })

                if new_rows:
                    st.session_state.kaizen_df = _ensure_ids(pd.concat(
                        [st.session_state.kaizen_df, pd.DataFrame(new_rows)], ignore_index=True
                    ))
                    # clear imported items from inbox
                    try:
                        uids = to_take["uid"].astype(str).tolist() if "uid" in to_take.columns else []
                        if uids:
                            delete_suggestions(username, namespace, project_id, uids)
                    except Exception:
                        pass

                    st.success(f"Imported {len(new_rows)} idea(s) into the Kaizen table.")

    st.divider()

    # ---- View selector: Table or Swimlane Board
    view_mode = st.radio(
        "View",
        options=["Table", "Swimlane Board"],
        index=0,
        key="kaizen_view_mode",
        horizontal=True,
    )

    # ---- TABLE VIEW (editable)
    if view_mode == "Table":
        st.subheader("Ideas (edit inline)")
        edf = st.data_editor(
            data_f,
            num_rows="dynamic",
            use_container_width=True,
            key="kaizen_ideas_editor",
            column_config={
                "ID": st.column_config.Column(disabled=True, help="Stable row ID"),
                "Area": st.column_config.SelectboxColumn(options=AREAS),
                "Type": st.column_config.SelectboxColumn(options=TYPES),
                "Status": st.column_config.SelectboxColumn(options=STATUSES),
                "Effort": st.column_config.SelectboxColumn(options=EFFORTS),
                "Monthly Benefit": st.column_config.NumberColumn(min_value=0, step=50),
                "One-off Cost": st.column_config.NumberColumn(min_value=0, step=50),
                "Start": st.column_config.DateColumn(),
                "Due": st.column_config.DateColumn(),
            },
        )
        # merge edits back
        data.loc[mask, :] = edf.values
        st.session_state.kaizen_df = _ensure_ids(data)

        st.divider()
        st.subheader("Pareto – Top Benefit Ideas")
        _pareto(data)

    # ---- SWIMLANE BOARD VIEW
    else:
        st.subheader("Swimlane Board")
        # columns per status
        cols = st.columns(len(STATUSES))
        for lane_idx, (status, col) in enumerate(zip(STATUSES, cols)):
            with col:
                # Lane header with WIP note for Trial
                if status == "Trial":
                    col.caption(f"{status} (WIP {trial_now}/{limit})")
                else:
                    col.caption(status)

                lane_df = data[data["Status"] == status].sort_values("Monthly Benefit", ascending=False)
                if lane_df.empty:
                    col.markdown("_empty_")
                    continue

                for _, r in lane_df.iterrows():
                    rid = int(r["ID"])
                    col.markdown(
                        f"**{r['Idea']}**  \n"
                        f"{r['Area']} • {r['Type']} • Effort: {r['Effort']}  \n"
                        f"Benefit/mo: {int(r['Monthly Benefit'])} • Cost: {int(r['One-off Cost'])}  \n"
                        f"Owner: {r['Owner']} • Due: {pd.to_datetime(r['Due']).date() if pd.notna(r['Due']) else '—'}"
                    )
                    bcol1, bcol2 = col.columns(2)

                    # Move left
                    prev_s = _prev_status(status)
                    if prev_s is None:
                        bcol1.button("—", key=f"kaizen_left_dis_{rid}", disabled=True)
                    else:
                        if bcol1.button("←", key=f"kaizen_left_{rid}"):
                            st.session_state.kaizen_df.loc[st.session_state.kaizen_df["ID"] == rid, "Status"] = prev_s
                            st.experimental_rerun()

                    # Move right (check WIP for Trial)
                    next_s = _next_status(status)
                    if next_s is None:
                        bcol2.button("—", key=f"kaizen_right_dis_{rid}", disabled=True)
                    else:
                        # If the *next* lane is Trial and WIP would exceed limit -> disable
                        going_to_trial = (next_s == "Trial")
                        would_exceed = (trial_now + 1) > limit
                        disable_forward = going_to_trial and would_exceed
                        label = "→" if not disable_forward else "→ (WIP full)"
                        if bcol2.button(label, key=f"kaizen_right_{rid}", disabled=disable_forward):
                            st.session_state.kaizen_df.loc[st.session_state.kaizen_df["ID"] == rid, "Status"] = next_s
                            st.experimental_rerun()

        st.divider()
        st.subheader("Pareto – Top Benefit Ideas")
        _pareto(data)

    # ---------------------------
    # Persistence (Save/Load) & Back
    # ---------------------------
    st.divider()
    st.subheader("Save / Load / Export")

    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "kaizen_tracker"
# Inbox from other tools (SMED, Andon, etc.)
    try:
        inbox = list_suggestions(username, namespace, project_id)
    except Exception:
        inbox = []

    c1, c2, c3, c4 = st.columns([1,1,1,2])
    with c1:
        if st.button("💾 Save", key="kaizen_save"):
            payload = {
                "meta": {
                    "saved_at": datetime.utcnow().isoformat(),
                    "wip_limit_trial": int(st.session_state.kaizen_wip_limit),
                },
                "ideas": (st.session_state.kaizen_df.assign(
                    Start=pd.to_datetime(st.session_state.kaizen_df["Start"], errors="coerce").dt.date.astype(str),
                    Due=pd.to_datetime(st.session_state.kaizen_df["Due"], errors="coerce").dt.date.astype(str),
                ).to_dict(orient="records")),
                "metrics": _portfolio_metrics(st.session_state.kaizen_df),
            }
            if save_project_doc:
                save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot:
                append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            # Update consolidated Ops Snapshot (only on Save)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")
    with c2:
        if st.button("📥 Load", key="kaizen_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved Kaizen data found for this project/namespace.")
            else:
                df = pd.DataFrame(payload.get("ideas", []))
                df = _coerce_date(df, "Start")
                df = _coerce_date(df, "Due")
                df = _coerce_num(df, "Monthly Benefit")
                df = _coerce_num(df, "One-off Cost")
                st.session_state.kaizen_df = _ensure_ids(df)
                # restore WIP limit if present
                w = payload.get("meta", {}).get("wip_limit_trial")
                if isinstance(w, int) and w > 0:
                    st.session_state.kaizen_wip_limit = w
                st.success("Loaded Kaizen data.")

    with c3:
        if st.button("↩ Back to Ops Hub", key="kaizen_back"):
            back_to_hub()

    with c4:
        _download(st.session_state.kaizen_df, "kaizen_tracker.csv", "Export CSV")

    # One-pager TXT
    if st.button("Generate one-pager (TXT)", key="kaizen_txt"):
        buf = io.StringIO()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        m = _portfolio_metrics(st.session_state.kaizen_df)
        buf.write(f"Kaizen Tracker — {namespace}\nGenerated: {now}\n\n")
        buf.write(f"Ideas: {len(st.session_state.kaizen_df)} | Monthly Benefit: {m['monthly_total']} | One-off Cost: {m['oneoff_total']}\n")
        buf.write(f"Payback (mo): {m['payback']} | Annual ROI (%): {m['roi_annual']}\n")
        buf.write(f"Trial WIP: {m['counts'].get('Trial', 0)} / {int(st.session_state.kaizen_wip_limit)}\n\n")
        for _, r in st.session_state.kaizen_df.sort_values("Monthly Benefit", ascending=False).iterrows():
            buf.write(
                f"- [{r['Status']}] {r['Idea']} ({r['Area']}/{r['Type']}) | "
                f"Benefit/mo: {int(r['Monthly Benefit'])} | Cost: {int(r['One-off Cost'])} | "
                f"Owner: {r['Owner']} | Due: {pd.to_datetime(r['Due']).date() if pd.notna(r['Due']) else '—'}\n"
            )
        st.download_button("Download one-pager (TXT)", buf.getvalue().encode("utf-8"), "kaizen_one_pager.txt", "text/plain")
