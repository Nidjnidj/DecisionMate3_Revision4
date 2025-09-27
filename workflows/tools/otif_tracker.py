# workflows/tools/otif_tracker.py
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

FLOWS = ["Inbound", "Outbound"]

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:daily_ops"

def _coerce_date(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns: df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df

def _coerce_num(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns: df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

def _default_rows() -> pd.DataFrame:
    today = pd.Timestamp.utcnow().date()
    return pd.DataFrame([
        {"Date": today, "Flow": "Outbound", "Partner": "Customer A", "Order ID": "SO-1001",
         "Promise Date": today, "Delivered Date": today, "Qty Ordered": 500, "Qty Delivered": 500, "Reason": ""},
        {"Date": today, "Flow": "Inbound", "Partner": "Supplier X", "Order ID": "PO-2002",
         "Promise Date": today, "Delivered Date": today, "Qty Ordered": 1000, "Qty Delivered": 900, "Reason": "Partial shipment"},
        {"Date": today, "Flow": "Outbound", "Partner": "Customer B", "Order ID": "SO-1003",
         "Promise Date": today, "Delivered Date": today, "Qty Ordered": 300, "Qty Delivered": 290, "Reason": "Stockout"},
    ])

def _compute_flags(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d = _coerce_date(d, "Promise Date")
    d = _coerce_date(d, "Delivered Date")
    d = _coerce_num(d, "Qty Ordered")
    d = _coerce_num(d, "Qty Delivered")
    d["On-time"] = (pd.to_datetime(d["Delivered Date"]) <= pd.to_datetime(d["Promise Date"]))
    d["In-full"] = (d["Qty Delivered"] >= d["Qty Ordered"])
    d["OTIF"]    = d["On-time"] & d["In-full"]
    return d

def _metrics(d: pd.DataFrame) -> dict:
    tot = int(len(d))
    ot  = int(d["On-time"].sum()) if tot else 0
    inf = int(d["In-full"].sum()) if tot else 0
    otif = int(d["OTIF"].sum()) if tot else 0
    return {
        "orders": tot,
        "on_time_pct": round(100.0 * ot / tot, 1) if tot else 0.0,
        "in_full_pct": round(100.0 * inf / tot, 1) if tot else 0.0,
        "otif_pct":    round(100.0 * otif / tot, 1) if tot else 0.0,
        "late_count": int((~d["On-time"]).sum()) if tot else 0,
        "short_count": int((~d["In-full"]).sum()) if tot else 0,
    }

def _bar_by_partner(d: pd.DataFrame):
    if d.empty:
        st.info("No data yet."); return
    s = d.groupby("Partner")["OTIF"].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(7,4))
    ax.bar(s.index.astype(str), (s.values * 100.0))
    ax.set_title("OTIF by Partner (%)"); ax.set_ylabel("%")
    ax.set_xticklabels(s.index.astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def render(T=None):
    if "otif_df" not in st.session_state:
        st.session_state.otif_df = _default_rows()

    st.title("🚚 OTIF Tracker")
    st.caption("On-Time-In-Full for inbound/outbound orders; partner view and reasons.")

    # Filters
    with st.expander("Filters", expanded=False):
        c1, c2, c3 = st.columns([1,1,2])
        with c1:
            f_flow = st.multiselect("Flow", FLOWS, default=FLOWS)
        with c2:
            partner = st.text_input("Partner (contains)", "")
        with c3:
            oid = st.text_input("Order ID (contains)", "")

    df = st.session_state.otif_df.copy()
    df = _coerce_date(df, "Date")
    df = _coerce_date(df, "Promise Date")
    df = _coerce_date(df, "Delivered Date")
    df = _coerce_num(df, "Qty Ordered")
    df = _coerce_num(df, "Qty Delivered")

    mask = df["Flow"].isin(f_flow)
    if partner.strip():
        mask &= df["Partner"].str.lower().str.contains(partner.strip().lower(), na=False)
    if oid.strip():
        mask &= df["Order ID"].str.lower().str.contains(oid.strip().lower(), na=False)

    view = df.loc[mask].reset_index(drop=True)

    dflags = _compute_flags(df)
    m = _metrics(dflags)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Orders", m["orders"])
    k2.metric("On-time %", f"{m['on_time_pct']:.1f}%")
    k3.metric("In-full %", f"{m['in_full_pct']:.1f}%")
    k4.metric("OTIF %", f"{m['otif_pct']:.1f}%")

    st.divider()
    st.subheader("Orders (edit inline)")

    edf = st.data_editor(
        view,
        num_rows="dynamic",
        use_container_width=True,
        key="otif_editor",
        column_config={
            "Flow": st.column_config.SelectboxColumn(options=FLOWS),
            "Date": st.column_config.DateColumn(),
            "Promise Date": st.column_config.DateColumn(),
            "Delivered Date": st.column_config.DateColumn(),
            "Qty Ordered": st.column_config.NumberColumn(min_value=0, step=10),
            "Qty Delivered": st.column_config.NumberColumn(min_value=0, step=10),
        },
    )
    # merge back edits into full df
    df.loc[mask, :] = edf.values
    st.session_state.otif_df = df

    st.divider()
    st.subheader("OTIF by Partner")
    _bar_by_partner(_compute_flags(df))

    # Save/Load/Back/Export
    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "otif_tracker"

    b1, b2, b3, b4 = st.columns([1,1,1,2])

    with b1:
        if st.button("💾 Save", key="otif_save"):
            flags = _compute_flags(st.session_state.otif_df)
            payload = {
                "meta": {"saved_at": datetime.utcnow().isoformat()},
                "rows": (flags.assign(
                    Date=pd.to_datetime(flags["Date"], errors="coerce").dt.date.astype(str),
                    **{"Promise Date": pd.to_datetime(flags["Promise Date"], errors="coerce").dt.date.astype(str)},
                    **{"Delivered Date": pd.to_datetime(flags["Delivered Date"], errors="coerce").dt.date.astype(str)},
                ).to_dict(orient="records")),
                "metrics": _metrics(flags),
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
        if st.button("📥 Load", key="otif_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved OTIF data found.")
            else:
                df2 = pd.DataFrame(payload.get("rows", []))
                for c in ("Date", "Promise Date", "Delivered Date"):
                    df2 = _coerce_date(df2, c)
                df2 = _coerce_num(df2, "Qty Ordered")
                df2 = _coerce_num(df2, "Qty Delivered")
                st.session_state.otif_df = df2
                st.success("Loaded OTIF data.")

    with b3:
        if st.button("↩ Back to Ops Hub", key="otif_back"):
            back_to_hub()

    with b4:
        out = st.session_state.otif_df.copy()
        for c in ("Date", "Promise Date", "Delivered Date"):
            out[c] = pd.to_datetime(out[c], errors="coerce").dt.date.astype(str)
        st.download_button("Export CSV", out.to_csv(index=False).encode("utf-8"), "otif_records.csv", "text/csv")
