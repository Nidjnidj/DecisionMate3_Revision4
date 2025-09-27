# workflows/tools/supplier_dev_a3.py
from __future__ import annotations

from datetime import datetime
import pandas as pd
import streamlit as st

# Optional persistence/history/back (graceful fallback)
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

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:small_projects"

def _coerce_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def _default_actions() -> pd.DataFrame:
    return pd.DataFrame([
        {"Action": "Confirm demand profile & MOQ", "Owner": "", "Due": pd.NaT, "Status": "Planned"},
        {"Action": "Set PFMEA / Control Plan review", "Owner": "", "Due": pd.NaT, "Status": "Planned"},
        {"Action": "Run pilot lot & PPAP", "Owner": "", "Due": pd.NaT, "Status": "Planned"},
    ])

def render(T=None):
    if "a3_actions" not in st.session_state:
        st.session_state.a3_actions = _default_actions()
    if "a3_meta" not in st.session_state:
        st.session_state.a3_meta = {
            "Supplier": "Supplier X",
            "Part": "Bracket-A",
            "Problem": "",
            "Current State": "",
            "Goal": "OTD ≥ 98%, PPM ≤ 500, Lead-time ≤ 12d",
            "Root Cause (key)": "",
            "Plan Summary": "",
            "Owner": "",
            "OTD %": 90.0,
            "PPM": 1200,
            "Lead-time (d)": 18,
        }

    st.title("🧾 Supplier Development A3 (Mini)")
    st.caption("Capture problem → analysis → countermeasures; track OTD/PPM/Lead-time.")

    with st.expander("Header", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.session_state.a3_meta["Supplier"] = st.text_input("Supplier", st.session_state.a3_meta["Supplier"])
        with c2:
            st.session_state.a3_meta["Part"] = st.text_input("Part", st.session_state.a3_meta["Part"])
        with c3:
            st.session_state.a3_meta["Owner"] = st.text_input("Owner", st.session_state.a3_meta["Owner"])
        with c4:
            st.session_state.a3_meta["Goal"] = st.text_input("Goal", st.session_state.a3_meta["Goal"])

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Problem / Current State")
        st.session_state.a3_meta["Problem"] = st.text_area("Problem", st.session_state.a3_meta["Problem"], height=120)
        st.session_state.a3_meta["Current State"] = st.text_area("Current State", st.session_state.a3_meta["Current State"], height=120)
    with c2:
        st.subheader("Root Cause / Plan")
        st.session_state.a3_meta["Root Cause (key)"] = st.text_area("Root Cause (key)", st.session_state.a3_meta["Root Cause (key)"], height=120)
        st.session_state.a3_meta["Plan Summary"] = st.text_area("Plan Summary", st.session_state.a3_meta["Plan Summary"], height=120)

    st.divider()
    st.subheader("Countermeasures / Actions")
    df = _coerce_date(st.session_state.a3_actions.copy(), "Due")
    edf = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="a3_actions_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn(options=STATUSES),
            "Due": st.column_config.DateColumn(),
        },
    )
    st.session_state.a3_actions = _coerce_date(edf, "Due")

    st.divider()
    st.subheader("Supplier Metrics")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.session_state.a3_meta["OTD %"] = st.number_input("OTD %", min_value=0.0, max_value=100.0, value=float(st.session_state.a3_meta["OTD %"]), step=0.1)
    with m2:
        st.session_state.a3_meta["PPM"] = st.number_input("PPM", min_value=0, value=int(st.session_state.a3_meta["PPM"]), step=50)
    with m3:
        st.session_state.a3_meta["Lead-time (d)"] = st.number_input("Lead-time (d)", min_value=0, value=int(st.session_state.a3_meta["Lead-time (d)"]), step=1)

    # Save / Load / Back / Export
    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "supplier_dev_a3"

    c1, c2, c3, c4 = st.columns([1,1,1,2])
    with c1:
        if st.button("💾 Save", key="a3_save"):
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "a3": st.session_state.a3_meta,
                "actions": (st.session_state.a3_actions.assign(
                    Due=pd.to_datetime(st.session_state.a3_actions["Due"], errors="coerce").dt.date.astype(str)
                ).to_dict(orient="records")),
            }
            if save_project_doc:
                save_project_doc(username, namespace, project_id, DOC_KEY, payload)
            if append_snapshot:
                append_snapshot(username, namespace, project_id, DOC_KEY, payload)
            # refresh consolidated snapshot (small_projects)
            try:
                from services.ops_snapshot import rebuild_snapshot
                rebuild_snapshot(username, namespace, project_id)
            except Exception:
                pass
            st.success(f"Saved to [{namespace}] / {DOC_KEY}")

    with c2:
        if st.button("📥 Load", key="a3_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved A3 data found.")
            else:
                st.session_state.a3_meta = payload.get("a3", st.session_state.a3_meta)
                st.session_state.a3_actions = _coerce_date(pd.DataFrame(payload.get("actions", [])), "Due")
                st.success("Loaded A3.")

    with c3:
        if st.button("↩ Back to Ops Hub", key="a3_back"):
            back_to_hub()

    with c4:
        # Export TXT
        txt = []
        a3 = st.session_state.a3_meta
        txt.append(f"Supplier: {a3['Supplier']}  |  Part: {a3['Part']}  |  Owner: {a3['Owner']}")
        txt.append(f"Goal: {a3['Goal']}")
        txt.append("\nProblem:\n" + a3["Problem"])
        txt.append("\nCurrent State:\n" + a3["Current State"])
        txt.append("\nRoot Cause (key):\n" + a3["Root Cause (key)"])
        txt.append("\nPlan Summary:\n" + a3["Plan Summary"])
        txt.append(f"\nMetrics: OTD={a3['OTD %']}% | PPM={a3['PPM']} | Lead-time={a3['Lead-time (d)']}d\n")
        for _, r in st.session_state.a3_actions.iterrows():
            txt.append(f"- {r['Action']} | Owner: {r['Owner']} | Due: {r['Due']} | Status: {r['Status']}")
        content = "\n".join(txt)
        st.download_button("Export TXT", content.encode("utf-8"), "supplier_a3.txt", "text/plain")
