# workflows/tools/kanban_replenishment.py
from __future__ import annotations
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
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

AREAS = ["Press Shop", "Welding", "Assembly", "Paint", "Logistics"]
STATUSES = ["OK", "Trigger", "Expedite"]

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:daily_ops"

def _coerce_num(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns: df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

def _default_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"Item": "R-0402-Res", "Area": "SMT-1", "Min": 2000, "Max": 6000, "On Hand": 2400, "In Transit": 0, "Card Size": 1000, "Status": "OK"},
        {"Item": "CAP-0603",   "Area": "SMT-2", "Min": 1500, "Max": 5000, "On Hand": 800,  "In Transit": 500, "Card Size": 1000, "Status": "Trigger"},
        {"Item": "Bracket-A",  "Area": "Assembly", "Min": 50, "Max": 150, "On Hand": 60, "In Transit": 0, "Card Size": 20, "Status": "OK"},
    ])

def _derive(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in ("Min","Max","On Hand","In Transit","Card Size"):
        d = _coerce_num(d, c)
    d["Available"] = d["On Hand"] + d["In Transit"]
    d["Shortage"]  = (d["Available"] < d["Min"])
    # Suggested order = max(0, Max - Available) rounded up to nearest card size (if card size > 0)
    raw = (d["Max"] - d["Available"]).clip(lower=0)
    cs  = d["Card Size"].replace(0, 1)  # avoid div/0
    d["Reorder Qty"] = ((raw + cs - 1) // cs) * cs
    # Suggested status
    d["Suggested Status"] = d.apply(
        lambda r: "Expedite" if r["Available"] <= r["Min"] // 2 else ("Trigger" if r["Available"] < r["Min"] else "OK"),
        axis=1,
    )
    return d

def _metrics(d: pd.DataFrame) -> dict:
    return {
        "sku": int(len(d)),
        "shortages": int(d["Shortage"].sum()) if "Shortage" in d.columns else 0,
        "to_order": int((d["Reorder Qty"] > 0).sum()),
        "reorder_total": int(d["Reorder Qty"].sum()),
    }

def _bar_reorder_by_area(d: pd.DataFrame):
    if d.empty:
        st.info("No data yet."); return
    s = d.groupby("Area")["Reorder Qty"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7,4))
    ax.bar(s.index.astype(str), s.values)
    ax.set_title("Recommended Replenishment by Area"); ax.set_ylabel("Qty")
    ax.set_xticklabels(s.index.astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def render(T=None):
    if "kanban_df" not in st.session_state:
        st.session_state.kanban_df = _default_rows()

    st.title("📦 Kanban Replenishment")
    st.caption("Min/Max cards, current stock vs in transit, triggers and recommended order qty.")

    with st.expander("Filters", expanded=False):
        c1, c2 = st.columns([1,2])
        with c1:
            area = st.text_input("Area contains", "")
        with c2:
            item = st.text_input("Item contains", "")

    df = st.session_state.kanban_df.copy()
    d = _derive(df)

    mask = pd.Series(True, index=d.index)
    if area.strip():
        mask &= d["Area"].str.lower().str.contains(area.strip().lower(), na=False)
    if item.strip():
        mask &= d["Item"].str.lower().str.contains(item.strip().lower(), na=False)

    view = d.loc[mask].reset_index(drop=True)

    m = _metrics(d)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("SKUs", m["sku"])
    k2.metric("Shortages", m["shortages"])
    k3.metric("Items to Order", m["to_order"])
    k4.metric("Total Recommended Qty", m["reorder_total"])

    st.divider()
    st.subheader("Kanban Table (edit inline)")
    edf = st.data_editor(
        view[["Item","Area","Min","Max","On Hand","In Transit","Card Size","Status"]],
        num_rows="dynamic",
        use_container_width=True,
        key="kanban_editor",
        column_config={
            "Status": st.column_config.SelectboxColumn(options=STATUSES),
            "Min": st.column_config.NumberColumn(min_value=0, step=10),
            "Max": st.column_config.NumberColumn(min_value=0, step=10),
            "On Hand": st.column_config.NumberColumn(min_value=0, step=10),
            "In Transit": st.column_config.NumberColumn(min_value=0, step=10),
            "Card Size": st.column_config.NumberColumn(min_value=0, step=1),
        },
    )
    # merge edits back to full df
    d.loc[mask, ["Item","Area","Min","Max","On Hand","In Transit","Card Size","Status"]] = edf.values
    st.session_state.kanban_df = d.drop(columns=["Available","Shortage","Reorder Qty","Suggested Status"], errors="ignore")

    st.divider()
    st.subheader("Recommended Replenishment by Area")
    _bar_reorder_by_area(_derive(st.session_state.kanban_df))

    # Save/Load/Back/Export
    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "kanban_replenishment"

    b1, b2, b3, b4 = st.columns([1,1,1,2])

    with b1:
        if st.button("💾 Save", key="kanban_save"):
            derived = _derive(st.session_state.kanban_df)
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": st.session_state.kanban_df.to_dict(orient="records"),
                "metrics": _metrics(derived),
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
        if st.button("📥 Load", key="kanban_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved Kanban data found.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                st.session_state.kanban_df = df2
                st.success("Loaded Kanban data.")

    with b3:
        if st.button("↩ Back to Ops Hub", key="kanban_back"):
            back_to_hub()

    with b4:
        out = st.session_state.kanban_df.copy()
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "kanban_table.csv", "text/csv")
