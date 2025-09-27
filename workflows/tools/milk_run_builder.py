# workflows/tools/milk_run_builder.py
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

def _namespace() -> str:
    industry = st.session_state.get("project_industry", st.session_state.get("industry", "manufacturing"))
    return f"{industry}:ops:small_projects"

def _coerce_num(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        df[col] = 0
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

def _default_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"Stop #": 1, "Supplier": "SUP-A", "Distance to next (km)": 12, "Dwell (min)": 10, "Planned Qty": 400, "Max Pallets": 6},
        {"Stop #": 2, "Supplier": "SUP-B", "Distance to next (km)": 18, "Dwell (min)": 12, "Planned Qty": 300, "Max Pallets": 4},
        {"Stop #": 3, "Supplier": "SUP-C", "Distance to next (km)": 25, "Dwell (min)": 8,  "Planned Qty": 500, "Max Pallets": 8},
    ])

def _metrics(df: pd.DataFrame, truck_capacity_pallets: int, avg_speed_kmh: float) -> dict:
    d = df.copy()
    for c in ("Distance to next (km)", "Dwell (min)", "Planned Qty", "Max Pallets"):
        d = _coerce_num(d, c)
    route_km = float(d["Distance to next (km)"].sum())
    drive_min = (route_km / max(avg_speed_kmh, 1e-6)) * 60.0
    dwell_min = float(d["Dwell (min)"].sum())
    total_min = drive_min + dwell_min
    pallets_used = int(d["Max Pallets"].sum())
    cap_over = max(0, pallets_used - int(truck_capacity_pallets))
    return dict(
        stops=len(d),
        route_km=round(route_km, 1),
        drive_min=int(round(drive_min)),
        dwell_min=int(round(dwell_min)),
        total_min=int(round(total_min)),
        pallets_used=pallets_used,
        capacity=truck_capacity_pallets,
        capacity_over=cap_over,
    )

def _chart_segments(df: pd.DataFrame):
    d = _coerce_num(df.copy(), "Distance to next (km)")
    if d.empty: 
        st.info("Add stops to see route distance segments.")
        return
    fig, ax = plt.subplots(figsize=(7,3.5))
    ax.bar(d["Supplier"].astype(str), d["Distance to next (km)"])
    ax.set_title("Segment distances (km)")
    ax.set_ylabel("km")
    ax.set_xticklabels(d["Supplier"].astype(str), rotation=30, ha="right")
    st.pyplot(fig)

def render(T=None):
    if "milk_df" not in st.session_state:
        st.session_state.milk_df = _default_rows()

    st.title("🗺️ Milk-Run Route Builder")
    st.caption("Plan stops, dwell, and capacity. Distances are segmental to next stop (loop).")

    with st.expander("Truck / Planning Inputs", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            truck_capacity = st.number_input("Truck capacity (pallets)", min_value=1, value=12, step=1, key="milk_cap")
        with c2:
            avg_speed = st.number_input("Average speed (km/h)", min_value=1, value=35, step=1, key="milk_speed")
        with c3:
            loop_pad = st.number_input("Loop buffer (min)", min_value=0, value=15, step=5, key="milk_pad")

    df = st.session_state.milk_df.copy()
    for c in ("Distance to next (km)", "Dwell (min)", "Planned Qty", "Max Pallets"):
        df = _coerce_num(df, c)

    st.subheader("Stops (edit inline)")
    edf = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="milk_editor",
        column_config={
            "Stop #": st.column_config.NumberColumn(min_value=1, step=1),
            "Distance to next (km)": st.column_config.NumberColumn(min_value=0, step=1),
            "Dwell (min)": st.column_config.NumberColumn(min_value=0, step=1),
            "Max Pallets": st.column_config.NumberColumn(min_value=0, step=1),
        },
    )
    st.session_state.milk_df = edf

    m = _metrics(edf, int(truck_capacity), float(avg_speed))
    m["total_min"] += int(loop_pad)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Stops", m["stops"])
    k2.metric("Route (km)", m["route_km"])
    k3.metric("Drive (min)", m["drive_min"])
    k4.metric("Dwell (min)", m["dwell_min"])
    k5.metric("Total (min)", m["total_min"])
    k6.metric("Pallets used / cap", f"{m['pallets_used']} / {m['capacity']}")
    if m["capacity_over"] > 0:
        st.error(f"Capacity exceeded by {m['capacity_over']} pallets")

    st.divider()
    st.subheader("Segment Distance Chart")
    _chart_segments(edf)

    # Save / Load / Back / Export
    st.divider()
    st.subheader("Save / Load / Export")
    namespace = _namespace()
    username   = st.session_state.get("username", "Guest")
    project_id = st.session_state.get("active_project_id") or "P-DEMO"
    DOC_KEY    = "milk_run_builder"

    c1, c2, c3, c4 = st.columns([1,1,1,2])
    with c1:
        if st.button("💾 Save", key="milk_save"):
            payload = {
                "meta": {
                    "saved_at": datetime.utcnow().isoformat(),
                    "truck_capacity": int(truck_capacity),
                    "avg_speed_kmh": float(avg_speed),
                    "loop_buffer_min": int(loop_pad),
                },
                "rows": st.session_state.milk_df.to_dict(orient="records"),
                "metrics": m,
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
        if st.button("📥 Load", key="milk_load"):
            payload = load_project_doc(username, namespace, project_id, DOC_KEY) if load_project_doc else None
            if not payload:
                st.info("No saved Milk-Run data found.")
            else:
                st.session_state.milk_df = pd.DataFrame(payload.get("rows", []))
                st.success("Loaded Milk-Run data.")

    with c3:
        if st.button("↩ Back to Ops Hub", key="milk_back"):
            back_to_hub()

    with c4:
        st.download_button("Export CSV", st.session_state.milk_df.to_csv(index=False).encode("utf-8"),
                           "milk_run_stops.csv", "text/csv")
