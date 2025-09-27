# workflows/ops_hub_green_energy.py
import streamlit as st
import datetime as dt

def render(T=None):
    """Green Energy Ops Hub. Returns a dict snapshot for autosave."""
    T = T or {}
    sub_mode = T.get("ops_mode", "daily_ops")

    st.subheader("🛠 Ops — Green Energy")

    if sub_mode == "daily_ops":
        st.markdown("### 🔋 Daily Ops — Green")
        d = st.date_input("Ops day", value=dt.date.today(), key="ge_ops_day")

        with st.expander("⚙️ Settings / Alerts", expanded=False):
            st.checkbox("Notify when availability < 90%", key="ge_alert_avail")
            st.checkbox("Notify when curtailment > 10% of forecast", key="ge_alert_curt")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            target_mwh = st.number_input("Target Energy (MWh/d)", min_value=0.0, value=500.0, step=10.0, key="ge_target_mwh")
        with col2:
            avail_pct = st.number_input("Availability (%)", min_value=0.0, max_value=100.0, value=96.0, step=0.1, key="ge_avail")
        with col3:
            curtail_mwh = st.number_input("Curtailment (MWh)", min_value=0.0, value=12.0, step=1.0, key="ge_curtail")
        with col4:
            defects_open = st.number_input("Open Defects", min_value=0, value=4, step=1, key="ge_defects")

        st.divider()
        st.markdown("#### Assets (edit inline)")
        typ = st.selectbox("Type", ["wind_farm", "solar_farm", "hydrogen"], key="ge_asset_type")
        if typ == "wind_farm":
            st.data_editor([
                {"Turbine": "WT-01", "Status": "On", "Power_MW": 5.8, "Wind_mps": 9.2},
                {"Turbine": "WT-02", "Status": "On", "Power_MW": 5.6, "Wind_mps": 9.0},
                {"Turbine": "WT-03", "Status": "Off", "Power_MW": 0.0, "Wind_mps": 0.0, "Reason": "Maintenance"},
            ], key="ge_assets_wind", num_rows="dynamic")
        elif typ == "solar_farm":
            st.data_editor([
                {"Inverter": "INV-01", "Status": "On", "AC_MW": 2.5, "Irr_kWm2": 0.75},
                {"Inverter": "INV-02", "Status": "On", "AC_MW": 2.6, "Irr_kWm2": 0.77},
            ], key="ge_assets_solar", num_rows="dynamic")
        else:  # hydrogen
            st.data_editor([
                {"Electrolyzer": "EL-01", "Status": "On", "H2_kgph": 210, "kWh_per_kg": 49.5},
                {"Electrolyzer": "EL-02", "Status": "Standby", "H2_kgph": 0, "kWh_per_kg": None},
            ], key="ge_assets_h2", num_rows="dynamic")

        return {
            "ops_mode": sub_mode,
            "date": str(d),
            "target_mwh": target_mwh,
            "availability_pct": avail_pct,
            "curtailment_mwh": curtail_mwh,
            "defects_open": defects_open,
            "asset_type": typ,
        }

    if sub_mode == "small_projects":
        st.markdown("### 🧰 Small Projects — Green")
        tbl = st.data_editor([
            {"ID": "GE-001", "Title": "Blade repair WT-03", "Due": "2025-09-10", "Owner": "Tech-A", "Status": "Planned"},
            {"ID": "GE-002", "Title": "Inverter firmware update", "Due": "2025-09-05", "Owner": "Tech-B", "Status": "In Progress"},
        ], key="ge_sp", num_rows="dynamic")
        return {"ops_mode": sub_mode, "backlog": tbl}

    # call_center not applicable → show neutral panel
    st.markdown("### ☎️ Call Center")
    st.info("No dedicated call-center workflow for Green Energy. Use Small Projects or Daily Ops.")
    return {"ops_mode": sub_mode, "note": "no_call_center"}
