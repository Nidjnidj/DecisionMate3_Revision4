# workflows/ops_hub_oil_gas.py
from __future__ import annotations
from typing import Dict, Any
import datetime as dt
import inspect
import streamlit as st
from ops_hub_common import render_for  # shared placeholders for non-daily modes

# ---- Optional deps (soft) ----
try:
    from fpdf import FPDF
except Exception:
    FPDF = None  # PDF export disabled if not installed

# ---- Artifact I/O (safe fallbacks) ----
try:
    from artifact_registry import save_artifact, get_latest
except Exception:
    def save_artifact(project_id, phase_id, workstream, a_type, data, status="Draft", sources=None):
        key = f"{project_id}::{phase_id}::{workstream}::{a_type}"
        buf = st.session_state.setdefault("_ops_artifacts", {})
        buf[key] = {"data": data, "status": status, "sources": sources, "ts": dt.datetime.utcnow().isoformat()}
        return {"artifact_id": key, "status": status}
    def get_latest(project_id, a_type, phase_id):
        key = f"{project_id}::{phase_id}::Ops::{a_type}"
        rec = (st.session_state.get("_ops_artifacts") or {}).get(key)
        if rec:
            return {"artifact_id": key, "data": rec["data"], "status": rec["status"], "ts": rec["ts"]}
        return None

# ---- helpers ----
def _ss_init(key: str, default):
    if key not in st.session_state:
        st.session_state[key] = default

def _today_iso() -> str:
    return dt.date.today().isoformat()

def _gas_to_boe(mmscf: float) -> float:
    # ~6 mscf ≈ 1 boe → 1 MMSCF = 1,000,000 scf ≈ 166.667 boe
    return float(mmscf * (1_000_000.0 / 6000.0))

def _make_pdf(payload: Dict[str, Any]) -> bytes:
    if not FPDF:
        return b""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Daily Ops — Shift Handover", ln=1, align="C")

    pdf.set_font("Arial", "", 11)
    day = payload.get("date", _today_iso())
    shift = payload.get("handover", {}).get("Shift", "Day")
    sup = payload.get("handover", {}).get("Supervisor", "")
    pdf.cell(0, 8, f"Date: {day}    Shift: {shift}    Supervisor: {sup}", ln=1)

    # KPIs
    tot = payload.get("totals", {})
    tgt = payload.get("targets", {})
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "KPIs", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Oil: {tot.get('oil_stbpd',0):,.0f} stb/d (Target {tgt.get('oil_stbpd',0):,.0f})", ln=1)
    pdf.cell(0, 6, f"Gas: {tot.get('gas_mmscfpd',0):,.1f} MMscf/d (Target {tgt.get('gas_mmscfpd',0):,.1f})", ln=1)
    pdf.cell(0, 6, f"Water: {tot.get('water_bwpd',0):,.0f} bwpd (Target {tgt.get('water_bwpd',0):,.0f})", ln=1)
    pdf.cell(0, 6, f"Deferment (total): {tot.get('defer_boe',0):,.0f} boe", ln=1)
    pdf.cell(0, 6, f"Uptime: {tot.get('uptime_pct',0):.1f}%", ln=1)

    # Wells
    pdf.ln(2); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Wells", ln=1)
    pdf.set_font("Arial", "", 10)
    for w in payload.get("wells", []):
        s = f"{w.get('Well','?')}: {w.get('Status','?')} | Oil {w.get('Oil_bpd',0):,.0f} bpd, Gas {w.get('Gas_mmscfpd',0):,.1f} MMscf/d, WHT {w.get('WHT_C',0)}°C, Choke {w.get('Choke_%',0)}%"
        if w.get("Deferment_boe", 0): s += f" | Defer {w['Deferment_boe']:,.0f} boe ({w.get('Reason','')})"
        pdf.multi_cell(0, 5, s)

    # Downtime
    pdf.ln(1); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Downtime / Deferment", ln=1)
    pdf.set_font("Arial", "", 10)
    for r in payload.get("downtime", []):
        s = f"{r.get('Start','')}–{r.get('End','')} | {r.get('Asset','')} | {r.get('Category','')} | {r.get('Cause','')} | Impact {r.get('Impact_boe',0)} boe"
        if r.get("Remarks"): s += f" | {r['Remarks']}"
        pdf.multi_cell(0, 5, s)

    # Emissions & Tanks
    emi = payload.get("emissions", {})
    pdf.ln(1); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Flaring & Emissions", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 6, f"Flaring: {emi.get('Flare_MMscfd',0)} MMscf/d   CO2e: {emi.get('CO2e_t',0)} t/d", ln=1)

    pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Tankage / Export", ln=1)
    pdf.set_font("Arial", "", 10)
    for t in payload.get("tankage", []):
        s = f"{t.get('Tank','?')}: Level {t.get('Level_bbl',0):,} bbl, BSW {t.get('BSW_%',0)}%, Temp {t.get('Temp_C',0)}°C, Export: {t.get('Export','')}"
        pdf.multi_cell(0, 5, s)

    # Notes
    pdf.ln(1); pdf.set_font("Arial", "B", 12); pdf.cell(0, 8, "Shift Notes / Actions", ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, f"Notes: {payload.get('handover',{}).get('Key_Notes','') or '—'}")
    pdf.multi_cell(0, 6, f"Actions: {payload.get('handover',{}).get('Actions','') or '—'}")
    return pdf.output(dest="S").encode("latin-1")

# ================= Daily Ops (rich O&G UI) =================
def daily_ops(T: Dict[str, Any]) -> Dict[str, Any]:
    project_id = st.session_state.get("active_project_id") or st.session_state.get("current_project_id") or "P-OPS"
    phase_id   = st.session_state.get("current_phase_id") or "PH-OPS"

    # Settings
    with st.expander("⚙️ Settings / Alerts", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.number_input("Alert: Flaring > (MMscf/d)", 0.0, 1e6, 5.0, 0.1, key="ops_thr_flare")
        c2.number_input("Alert: Uptime < (%)", 0.0, 100.0, 95.0, 0.5, key="ops_thr_uptime")
        c3.number_input("Alert: TRIR (MTD) >", 0.0, 100.0, 0.5, 0.1, key="ops_thr_trir")
        st.checkbox("Auto-compute TOTAL deferment vs targets", value=True, key="ops_auto_def_total")
        st.checkbox("Auto-fill per-well deferment (even split across OFF/SHUT-IN)", value=False, key="ops_auto_def_perwell")
        st.number_input("Assumed potential per OFF/SHUT-IN well (stb/d)", 0.0, 100_000.0, 500.0, 50.0, key="ops_assumed_pot")

    # Day & targets
    st.subheader("⛽ Daily Ops — Oil & Gas")
    colD, colT = st.columns([1, 2])
    with colD:
        day = st.date_input("Ops day", value=dt.date.today())
    with colT:
        target_oil = st.number_input("Target Oil (stb/d)", 0.0, 1e7, 100_000.0, 100.0)
        target_gas = st.number_input("Target Gas (MMscf/d)", 0.0, 1e5, 120.0, 0.1)
        target_wat = st.number_input("Expected Water (bwpd)", 0.0, 1e7, 20_000.0, 100.0)

    # Init tables
    _ss_init("ops_wells", [
        {"Well": "W-01", "Status": "On",  "Oil_bpd": 12000.0, "Gas_mmscfpd": 14.0, "Water_bpd": 1500.0,
         "WHP_bar": 120.0, "WHT_C": 65.0, "Choke_%": 40.0, "Deferment_boe": 0.0, "Reason": "", "Notes": ""},
        {"Well": "W-02", "Status": "On",  "Oil_bpd": 9800.0,  "Gas_mmscfpd": 11.0, "Water_bpd": 1800.0,
         "WHP_bar": 110.0, "WHT_C": 62.0, "Choke_%": 38.0, "Deferment_boe": 0.0, "Reason": "", "Notes": ""},
        {"Well": "W-03", "Status": "Off", "Oil_bpd": 0.0,     "Gas_mmscfpd": 0.0,  "Water_bpd": 0.0,
         "WHP_bar": 0.0,   "WHT_C": 0.0,  "Choke_%": 0.0,  "Deferment_boe": 500.0, "Reason": "ESP", "Notes": "Awaiting spare"},
    ])
    _ss_init("ops_downtime", [
        {"Start": f"{_today_iso()} 00:00", "End": f"{_today_iso()} 02:30", "Asset": "W-03", "Category": "Equipment",
         "Cause": "ESP trip", "Impact_boe": 500.0, "Remarks": "Restart planned"},
    ])
    _ss_init("ops_handover", {"Shift": "Day", "Supervisor": "", "Crew": "", "Key_Notes": "", "Actions": ""})
    _ss_init("ops_ptw", {"Issued": 5, "Active": 3, "Hot": 1, "Cold": 2, "Confined": 0})
    _ss_init("ops_hse", {"TRIR_MTD": 0.0, "LTI_MTD": 0, "NearMiss": 0, "Obs": 4})
    _ss_init("ops_emissions", {"Flare_MMscfd": 2.5, "CO2e_t": 310.0})
    _ss_init("ops_tanks", [
        {"Tank": "TK-01", "Level_bbl": 45000, "BSW_%": 0.7, "Temp_C": 35.0, "Export": "Available"},
        {"Tank": "TK-02", "Level_bbl": 38000, "BSW_%": 0.6, "Temp_C": 34.0, "Export": "Loading 18:00"},
    ])

    # KPIs
    oil_total = sum(max(0.0, r.get("Oil_bpd", 0.0)) for r in st.session_state.ops_wells if (r.get("Status") or "").lower() == "on")
    gas_total = sum(max(0.0, r.get("Gas_mmscfpd", 0.0)) for r in st.session_state.ops_wells if (r.get("Status") or "").lower() == "on")
    wat_total = sum(max(0.0, r.get("Water_bpd", 0.0)) for r in st.session_state.ops_wells if (r.get("Status") or "").lower() == "on")

    defer_total_boe = 0.0
    if st.session_state.get("ops_auto_def_total", True):
        oil_gap_boe = max(0.0, target_oil - oil_total)
        gas_gap_boe = _gas_to_boe(max(0.0, target_gas - gas_total))
        defer_total_boe = oil_gap_boe + gas_gap_boe

    if st.session_state.get("ops_auto_def_perwell", False) and defer_total_boe > 0:
        off_wells = [w for w in st.session_state.ops_wells if (w.get("Status","").lower() != "on")]
        if off_wells:
            each = defer_total_boe / max(1, len(off_wells))
            for w in st.session_state.ops_wells:
                if (w.get("Status","").lower() != "on"):
                    w["Deferment_boe"] = float(each)

    off_count = len([r for r in st.session_state.ops_wells if (r.get("Status") or "").lower() != "on"])
    uptime_pct = 100.0 - min(100.0, off_count * 5.0)

    # Alerts
    if st.session_state.ops_emissions.get("Flare_MMscfd", 0.0) > st.session_state.get("ops_thr_flare", 5.0):
        st.error("🚨 Flaring above threshold")
    if uptime_pct < st.session_state.get("ops_thr_uptime", 95.0):
        st.warning("⚠️ Uptime below threshold")
    if st.session_state.ops_hse.get("LTI_MTD", 0) > 0:
        st.error("🚨 LTI reported this month")
    if st.session_state.ops_hse.get("TRIR_MTD", 0.0) > st.session_state.get("ops_thr_trir", 0.5):
        st.warning("⚠️ TRIR above threshold")

    # KPI row
    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Oil (stb/d)", f"{oil_total:,.0f}", f"vs {target_oil:,.0f}")
    c2.metric("Gas (MMscf/d)", f"{gas_total:,.1f}", f"vs {target_gas:,.1f}")
    c3.metric("Water (bwpd)", f"{wat_total:,.0f}", f"vs {target_wat:,.0f}")
    c4.metric("Deferment (boe)", f"{defer_total_boe:,.0f}")
    c5.metric("Uptime (%)", f"{uptime_pct:.1f}")

    # Tabs
    tabs = st.tabs([
        "Wells & Production", "Downtime / Deferment", "Shift Handover",
        "HSE & PTW", "Flaring & Emissions", "Tankage / Export", "Overview & Save"
    ])

    with tabs[0]:
        st.markdown("### Wells & Production (edit inline)")
        cfg = {
            "Status": st.column_config.SelectboxColumn(options=["On", "Off", "Shut-in"]),
            "Choke_%": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0),
        }
        st.session_state.ops_wells = st.data_editor(
            st.session_state.ops_wells, num_rows="dynamic", hide_index=True, column_config=cfg, key="wells_editor"
        )

    with tabs[1]:
        st.markdown("### Downtime / Deferment Log")
        cfg = {
            "Category": st.column_config.SelectboxColumn(options=["Equipment", "Flowline", "Power", "Reservoir", "Other"]),
            "Start": st.column_config.TextColumn(help="YYYY-MM-DD HH:MM"),
            "End":   st.column_config.TextColumn(help="YYYY-MM-DD HH:MM"),
        }
        st.session_state.ops_downtime = st.data_editor(
            st.session_state.ops_downtime, num_rows="dynamic", hide_index=True, column_config=cfg, key="dt_editor"
        )

    with tabs[2]:
        st.markdown("### Shift Handover")
        colA, colB, colC = st.columns(3)
        st.session_state.ops_handover["Shift"] = colA.selectbox("Shift", ["Day", "Night"], index=0 if st.session_state.ops_handover.get("Shift") != "Night" else 1)
        st.session_state.ops_handover["Supervisor"] = colB.text_input("Supervisor", value=st.session_state.ops_handover.get("Supervisor", ""))
        st.session_state.ops_handover["Crew"] = colC.text_input("Crew", value=st.session_state.ops_handover.get("Crew", ""))
        st.session_state.ops_handover["Key_Notes"] = st.text_area("Key Notes / Events", value=st.session_state.ops_handover.get("Key_Notes",""))
        st.session_state.ops_handover["Actions"]   = st.text_area("Action Items / Follow-ups", value=st.session_state.ops_handover.get("Actions",""))

    with tabs[3]:
        st.markdown("### HSE & PTW")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**HSE Snapshot (MTD)**")
            st.session_state.ops_hse["TRIR_MTD"] = st.number_input("TRIR (MTD)", 0.0, 100.0, float(st.session_state.ops_hse.get("TRIR_MTD", 0.0)))
            st.session_state.ops_hse["LTI_MTD"]  = st.number_input("LTIs (MTD)", 0, 100, int(st.session_state.ops_hse.get("LTI_MTD", 0)))
            st.session_state.ops_hse["NearMiss"] = st.number_input("Near Misses (MTD)", 0, 1000, int(st.session_state.ops_hse.get("NearMiss", 0)))
            st.session_state.ops_hse["Obs"]      = st.number_input("HSE Observations (MTD)", 0, 1000, int(st.session_state.ops_hse.get("Obs", 0)))
        with col2:
            st.write("**PTW Snapshot (Today)**")
            st.session_state.ops_ptw["Issued"]   = st.number_input("Permits Issued", 0, 9999, int(st.session_state.ops_ptw.get("Issued", 0)))
            st.session_state.ops_ptw["Active"]   = st.number_input("Permits Active", 0, 9999, int(st.session_state.ops_ptw.get("Active", 0)))
            st.session_state.ops_ptw["Hot"]      = st.number_input("Hot Work", 0, 9999, int(st.session_state.ops_ptw.get("Hot", 0)))
            st.session_state.ops_ptw["Cold"]     = st.number_input("Cold Work", 0, 9999, int(st.session_state.ops_ptw.get("Cold", 0)))
            st.session_state.ops_ptw["Confined"] = st.number_input("Confined Space", 0, 9999, int(st.session_state.ops_ptw.get("Confined", 0)))

    with tabs[4]:
        st.markdown("### Flaring & Emissions")
        st.session_state.ops_emissions["Flare_MMscfd"] = st.number_input(
            "Flaring (MMscf/d)", 0.0, 1e6, float(st.session_state.ops_emissions.get("Flare_MMscfd", 0.0)), 0.1
        )
        st.session_state.ops_emissions["CO2e_t"] = st.number_input(
            "CO₂e (t/d)", 0.0, 1e7, float(st.session_state.ops_emissions.get("CO2e_t", 0.0)), 1.0
        )
        st.caption("CO₂e can be estimated from flaring volume and composition; enter measured or calculated value.")

    with tabs[5]:
        st.markdown("### Tankage / Export")
        cfg = {"Export": st.column_config.SelectboxColumn(options=["Available", "Loading", "Shut-in", "Unavailable"])}
        st.session_state.ops_tanks = st.data_editor(
            st.session_state.ops_tanks, num_rows="dynamic", hide_index=True, column_config=cfg, key="tnk_editor"
        )

    with tabs[6]:
        st.markdown("### Overview")
        colX, colY, colZ = st.columns(3)
        colX.metric("Oil (stb/d)", f"{oil_total:,.0f}", f"Δ {oil_total - target_oil:+,.0f}")
        colY.metric("Gas (MMscf/d)", f"{gas_total:,.1f}", f"Δ {gas_total - target_gas:+,.1f}")
        colZ.metric("Uptime (%)", f"{uptime_pct:.1f}")

        st.divider()
        left, right = st.columns([2,1])
        with left:
            st.markdown("**Shift Notes**")
            st.write(st.session_state.ops_handover.get("Key_Notes","") or "—")
        with right:
            st.markdown("**PTW (today)**")
            st.json(st.session_state.ops_ptw)

        st.divider()
        payload = {
            "date": day.isoformat(),
            "targets": {"oil_stbpd": target_oil, "gas_mmscfpd": target_gas, "water_bwpd": target_wat},
            "totals":  {"oil_stbpd": oil_total, "gas_mmscfpd": gas_total, "water_bwpd": wat_total,
                        "defer_boe": defer_total_boe, "uptime_pct": uptime_pct},
            "wells": st.session_state.ops_wells,
            "downtime": st.session_state.ops_downtime,
            "handover": st.session_state.ops_handover,
            "hse": st.session_state.ops_hse,
            "ptw": st.session_state.ops_ptw,
            "emissions": st.session_state.ops_emissions,
            "tankage": st.session_state.ops_tanks,
        }

        cA, cB, cC = st.columns([1,1,1])
        if cA.button("💾 Save Daily Ops Snapshot"):
            save_artifact(project_id, phase_id, "Ops", "Daily_Ops_Log", payload, status="Approved")
            st.success("Daily Ops snapshot saved (Ops/Daily_Ops_Log).")

        if cB.button("📄 Generate Handover PDF"):
            if FPDF is None:
                st.error("FPDF not installed. `pip install fpdf` to enable PDF export.")
            else:
                st.session_state["_ops_pdf"] = _make_pdf(payload)
                st.success("PDF generated, ready to download.")
        if "_ops_pdf" in st.session_state and isinstance(st.session_state["_ops_pdf"], (bytes, bytearray)):
            st.download_button(
                "⬇️ Download Handover PDF",
                data=st.session_state["_ops_pdf"],
                file_name=f"Daily_Ops_Handover_{day.isoformat()}.pdf",
                mime="application/pdf",
            )

        if cC.button("📥 Load Latest Daily Ops"):
            latest = get_latest(project_id, "Daily_Ops_Log", phase_id)
            if latest and isinstance(latest.get("data"), dict):
                d = latest["data"]
                st.session_state.ops_wells = d.get("wells", st.session_state.ops_wells)
                st.session_state.ops_downtime = d.get("downtime", st.session_state.ops_downtime)
                st.session_state.ops_handover = d.get("handover", st.session_state.ops_handover)
                st.session_state.ops_hse = d.get("hse", st.session_state.ops_hse)
                st.session_state.ops_ptw = d.get("ptw", st.session_state.ops_ptw)
                st.session_state.ops_emissions = d.get("emissions", st.session_state.ops_emissions)
                st.session_state.ops_tanks = d.get("tankage", st.session_state.ops_tanks)
                st.success("Loaded latest Daily_Ops_Log into the UI.")

    return {
        "ops_mode": "daily_ops",
        "date": day.isoformat(),
        "oil_total": oil_total, "gas_total": gas_total, "water_total": wat_total,
        "defer_boe": defer_total_boe, "uptime_pct": uptime_pct,
        "targets": {"oil": target_oil, "gas": target_gas, "water": target_wat},
    }

# ================= Small Projects / Call Center =================
def small_projects(*_, **__):
    st.subheader("Oil & Gas — Small Projects (placeholder)")
    st.info("Use the shared ops board here, or replace with your real backlog once ready.")

def call_center(*_, **__):
    st.subheader("Oil & Gas — Call Center (placeholder)")
    st.info("Wire up NOC/contact-center metrics here, or provide an `ops_call_center.py`.")

# ================= Entry point (accepts both styles) =================
INDUSTRY_KEY = "oil_gas"
LABEL = "Oil & Gas"

def render(T: Dict[str, Any] | None = None,
           industry: str = INDUSTRY_KEY,
           submode: str = "daily_ops",
           **kwargs):
    """
    Compatible with both:
      - render(T={...})  (Rev3/Rev4 pattern passing ops_mode in T)
      - render(industry="oil_gas", submode="small_projects")
    """
    # Prefer sidebar/session radio, then T, then argument
    sm = st.session_state.get("ops_mode") or ((T or {}).get("ops_mode") if isinstance(T, dict) else None) or (submode or "daily_ops")
    sm = str(sm).strip() or "daily_ops"

    if sm == "daily_ops":
        return daily_ops({"ops_mode": "daily_ops"})

    # For small_projects / call_center (and any future mode), use common renderer
    return render_for(INDUSTRY_KEY, LABEL, submode=sm, industry=industry, **kwargs)
