# engineering.py — Green & O&G friendly Engineering step (single entry point)
import streamlit as st
from typing import Dict, Any
from artifact_registry import save_artifact, approve_artifact, get_latest

STATUS_COLORS = {
    "Missing":  "#9AA0A6",
    "Pending":  "#F2C94C",
    "Draft":    "#F2994A",
    "Approved": "#27AE60",
}

def _initial_status():
    # mirror your app's CASCADE_MODE behavior (keep simple here)
    return "Pending"

def _status_chip(label: str, status: str):
    color = STATUS_COLORS.get(status, "#9AA0A6")
    st.markdown(
        f"<span style='display:inline-flex;align-items:center;gap:.5rem;"
        f"padding:.25rem .6rem;border-radius:999px;border:1px solid #eee'>"
        f"<span style='width:.6rem;height:.6rem;border-radius:50%;background:{color}'></span>"
        f"{label} — {status}</span>",
        unsafe_allow_html=True,
    )

def _save_all(project_id: str, phase_id: str, pfd: Dict[str, Any], equip: Dict[str, Any], util: Dict[str, Any], status="Draft"):
    save_artifact(project_id, phase_id, "Engineering", "PFD_Package", pfd, status=status)
    save_artifact(project_id, phase_id, "Engineering", "Equipment_List", equip, status=status)
    save_artifact(project_id, phase_id, "Engineering", "Utilities_Load", util, status=status)

def _approve_latest(project_id: str, phase_id: str, t: str):
    rec = get_latest(project_id, t, phase_id)
    if rec and rec.get("status") != "Approved":
        approve_artifact(project_id, rec["artifact_id"])

def run(stage: str):
    """Unified Engineering step for O&G + Green (wind/solar/hydrogen)."""
    st.markdown("#### Engineering — Process Simulation & Equipment List")

    project_id = st.session_state.get("current_project_id", "P-DEMO")
    phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")
    industry   = st.session_state.get("project_industry", st.session_state.get("industry", "oil_gas"))
    proj_type  = str(st.session_state.get("green_project_type", "wind")).lower()
    # ------------------------------------------------------------------
    # IT branch: requirements → MVP → test plan (Engineering artifacts)
    # ------------------------------------------------------------------
    if industry == "it":
        st.caption("IT Engineering: capture requirements, MVP release notes, and the test plan.")

        # --- Inputs ----------------------------------------------------
        st.subheader("Requirements")
        req_title = st.text_input("Requirements title", "User Authentication & Access Control")
        req_desc  = st.text_area("Requirements summary",
                                 "As a user, I can sign up, sign in, reset password; roles: admin, editor, viewer.")
        req_scope = st.text_area("In scope (comma-separated)",
                                 "Sign up, Sign in, Forgot password, Role-based access")
        req_out   = st.text_area("Out of scope (comma-separated)",
                                 "SSO integration, MFA rollout")

        st.subheader("MVP Release Notes")
        mvp_ver   = st.text_input("Version tag", "v0.1.0")
        mvp_high  = st.text_area("Highlights (bullets)",
                                 "- Basic auth flows\n- RBAC with 3 roles\n- Audit log MVP")

        st.subheader("Test Plan / QA")
        qa_owner  = st.text_input("QA owner", "qa.lead@example.com")
        qa_scope  = st.text_area("Test scope (bullets)",
                                 "- Unit tests for services\n- API contract tests\n- Happy path e2e for auth")
        qa_risks  = st.text_area("Known risks (bullets)",
                                 "- Password reset deliverability\n- Race conditions on role updates")

        # --- Build payloads -------------------------------------------
        req_payload = {
            "title": req_title,
            "summary": req_desc,
            "in_scope": [s.strip() for s in req_scope.split(",") if s.strip()],
            "out_of_scope": [s.strip() for s in req_out.split(",") if s.strip()],
        }
        mvp_payload = {
            "version": mvp_ver,
            "highlights_md": mvp_high,
        }
        qa_payload = {
            "owner": qa_owner,
            "scope_md": qa_scope,
            "risks_md": qa_risks,
        }

        # --- Save/Approve buttons -------------------------------------
        colA, colB, colC = st.columns(3)
        with colA:
            if st.button("💾 Save all (Draft)", use_container_width=True, key="it_save_draft"):
                save_artifact(project_id, phase_id, "Engineering", "Requirements_Document", req_payload, status="Draft")
                save_artifact(project_id, phase_id, "Engineering", "MVP_Release_Notes",   mvp_payload, status="Draft")
                save_artifact(project_id, phase_id, "Engineering", "Test_Plan_QA",         qa_payload,  status="Draft")
                st.success("Saved Requirements, MVP Release Notes, and Test Plan (Draft).")
        with colB:
            if st.button("💾 Save all (Pending)", use_container_width=True, key="it_save_pending"):
                save_artifact(project_id, phase_id, "Engineering", "Requirements_Document", req_payload, status=_initial_status())
                save_artifact(project_id, phase_id, "Engineering", "MVP_Release_Notes",   mvp_payload, status=_initial_status())
                save_artifact(project_id, phase_id, "Engineering", "Test_Plan_QA",         qa_payload,  status=_initial_status())
                st.success("Saved all as Pending.")
        with colC:
            if st.button("✅ Save & Approve all", use_container_width=True, key="it_save_approve"):
                rec1 = save_artifact(project_id, phase_id, "Engineering", "Requirements_Document", req_payload, status="Pending")
                rec2 = save_artifact(project_id, phase_id, "Engineering", "MVP_Release_Notes",   mvp_payload,   status="Pending")
                rec3 = save_artifact(project_id, phase_id, "Engineering", "Test_Plan_QA",         qa_payload,    status="Pending")
                for rec in (rec1, rec2, rec3):
                    approve_artifact(project_id, rec["artifact_id"])
                st.success("Approved Requirements, MVP Release Notes, and Test Plan.")

        # --- Status chips ---------------------------------------------
        st.caption("Latest statuses")
        for t in ("Requirements_Document", "MVP_Release_Notes", "Test_Plan_QA"):
            rec = get_latest(project_id, t, phase_id)
            _status_chip(t, (rec or {}).get("status", "Missing"))

        # Stop here so the Green/O&G branches below don't run
        return

    # ------------------------------------------------------------------
    # Branch per industry/type (but artifacts kept consistent)
    # ------------------------------------------------------------------
    if industry == "green_energy":
        if proj_type == "wind":
            st.caption("Quick sizing for Wind: farm capacity, substation & export cable loads.")
            col1, col2, col3 = st.columns(3)
            with col1:
                n_turb = st.number_input("Turbines (qty)", 1, 500, 20)
            with col2:
                mw_turb = st.number_input("Rated power per turbine (MW)", 1.0, 20.0, 8.0, step=0.5)
            with col3:
                cf = st.number_input("Capacity factor (%)", 10.0, 70.0, 42.0, step=0.5)

            farm_mw   = n_turb * mw_turb
            aep_gwh   = farm_mw * (cf/100.0) * 8760.0 / 1000.0  # GWh/yr
            st.metric("Farm capacity (MW)", f"{farm_mw:,.1f}")
            st.metric("Est. AEP (GWh/yr)", f"{aep_gwh:,.0f}")

            # simple BOP/equipment
            equip = {
                "items": [
                    {"tag": "WTG", "type": "Wind Turbine", "duty": mw_turb, "qty": int(n_turb), "lead_weeks": 52},
                    {"tag": "OSS-TR", "type": "Offshore Substation Transformer", "duty": farm_mw*1.1, "qty": 2, "lead_weeks": 40},
                    {"tag": "EX-CABLE", "type": "Export Cable System", "duty": farm_mw, "qty": 1, "lead_weeks": 36},
                ]
            }
            # utilities: electrical only
            util = {
                "power_demand_profile": [farm_mw*0.02],  # parasitics during ops (rough)
                "steam_cold_duty": 0.0, "fuel_gas": 0.0,
                "cooling_water": 0.0, "instrument_air": 0.5,
            }
            pfd = {
                "pfd_svg_ref": "wind_block_diagram.svg",
                "stream_table": [
                    {"id": "Grid", "P": 220, "flow_power_mw": farm_mw, "phase": "E"},
                ],
                "notes": {"capacity_mw": farm_mw, "aep_gwh": aep_gwh}
            }

        elif proj_type == "solar":
            st.caption("Quick sizing for Solar PV: DC array, inverter block and AC collection.")
            col1, col2, col3 = st.columns(3)
            with col1:
                dc_mw = st.number_input("DC capacity (MWdc)", 1.0, 1000.0, 200.0, step=1.0)
            with col2:
                dc_ac_ratio = st.number_input("DC/AC ratio", 1.0, 2.0, 1.25, step=0.05)
            with col3:
                cf = st.number_input("Capacity factor (%)", 10.0, 35.0, 22.0, step=0.5)

            ac_mw   = dc_mw / max(0.1, dc_ac_ratio)
            aep_gwh = ac_mw * (cf/100.0) * 8760.0 / 1000.0
            st.metric("AC capacity (MWac)", f"{ac_mw:,.1f}")
            st.metric("Est. AEP (GWh/yr)", f"{aep_gwh:,.0f}")

            equip = {
                "items": [
                    {"tag": "PV-STR", "type": "PV String/Tracker Blocks", "duty": dc_mw, "qty": 1, "lead_weeks": 24},
                    {"tag": "INV", "type": "Inverters", "duty": ac_mw, "qty": max(1, int(ac_mw/3)), "lead_weeks": 26},
                    {"tag": "AC-TR", "type": "Collector Transformers", "duty": ac_mw*1.1, "qty": max(1, int(ac_mw/50)), "lead_weeks": 30},
                ]
            }
            util = {
                "power_demand_profile": [ac_mw*0.01],  # parasitics
                "steam_cold_duty": 0.0, "fuel_gas": 0.0,
                "cooling_water": 0.0, "instrument_air": 0.3,
            }
            pfd = {
                "pfd_svg_ref": "solar_block_diagram.svg",
                "stream_table": [
                    {"id": "Grid", "P": 110, "flow_power_mw": ac_mw, "phase": "E"},
                ],
                "notes": {"capacity_mw_ac": ac_mw, "aep_gwh": aep_gwh}
            }

        else:  # hydrogen
            st.caption("Quick sizing for Hydrogen: electrolyzer + BOP, sized from demand.")
            col1, col2, col3 = st.columns(3)
            with col1:
                demand_tpd = st.number_input("Hydrogen demand (t/day)", 1.0, 500.0, 50.0, step=1.0)
            with col2:
                spec_kwh_per_kg = st.number_input("Electrolyzer specific energy (kWh/kg)", 35.0, 65.0, 50.0, step=0.5)
            with col3:
                stack_mw = st.number_input("Stack unit size (MW)", 1.0, 100.0, 20.0, step=1.0)

            kgph = demand_tpd * 1000.0 / 24.0
            req_mw = kgph * spec_kwh_per_kg / 1000.0
            stacks = max(1, int(round(req_mw / stack_mw)))

            st.metric("Required power (MW)", f"{req_mw:,.1f}")
            st.metric("Electrolyzer stacks (qty)", f"{stacks}")

            equip = {
                "items": [
                    {"tag": "ELZ", "type": "Electrolyzer Stack", "duty": stack_mw, "qty": stacks, "lead_weeks": 40},
                    {"tag": "REC", "type": "Rectifier/Power Conditioning", "duty": req_mw*1.05, "qty": 1, "lead_weeks": 36},
                    {"tag": "COMP", "type": "H2 Compressor", "duty": kgph, "qty": 1, "lead_weeks": 30},
                    {"tag": "DRY", "type": "Dryer/Purifier", "duty": kgph, "qty": 1, "lead_weeks": 28},
                ]
            }
            util = {
                "power_demand_profile": [req_mw],
                "steam_cold_duty": 0.0, "fuel_gas": 0.0,
                "cooling_water": 50.0, "instrument_air": 5.0,
            }
            pfd = {
                "pfd_svg_ref": "hydrogen_block_diagram.svg",
                "stream_table": [
                    {"id": "H2", "flow_mass_kgph": kgph, "purity_pct": 99.9, "P": 30, "phase": "G"},
                ],
                "notes": {"required_mw": req_mw, "stacks": stacks}
            }

    else:
        # O&G fallback: tiny demo PFD & equipment (kept consistent with your seeding)
        st.caption("Oil & Gas process quick stub (replace with your detailed sim).")
        duty = st.number_input("Process duty (kW)", 1000.0, 500000.0, 50000.0, step=1000.0)
        equip = {
            "items": [
                {"tag": "HX-101", "type": "Exchanger", "duty": duty, "qty": 1, "lead_weeks": 22},
                {"tag": "P-101",  "type": "Pump", "duty": duty/10, "qty": 2, "lead_weeks": 16},
            ]
        }
        util = {"power_demand_profile": [duty/1000.0], "steam_cold_duty": 1.2, "fuel_gas": 0.3,
                "cooling_water": 15.0, "instrument_air": 5.0}
        pfd  = {"pfd_svg_ref": "pfd_demo.svg", "stream_table": [{"id":"S1","T":60,"P":10,"phase":"L","flow_mass":100.0}]}

    st.divider()
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("💾 Save (Draft)", use_container_width=True, key="eng_save_draft"):
            _save_all(project_id, phase_id, pfd, equip, util, status="Draft")
            st.success("Engineering artifacts saved (Draft).")
    with c2:
        if st.button("💾 Save (Pending)", use_container_width=True, key="eng_save_pending"):
            _save_all(project_id, phase_id, pfd, equip, util, status=_initial_status())
            st.success("Engineering artifacts saved (Pending).")
    with c3:
        if st.button("✅ Save & Approve", use_container_width=True, key="eng_save_approve"):
            _save_all(project_id, phase_id, pfd, equip, util, status="Pending")
            _approve_latest(project_id, phase_id, "PFD_Package")
            _approve_latest(project_id, phase_id, "Equipment_List")
            _approve_latest(project_id, phase_id, "Utilities_Load")
            st.success("Engineering artifacts approved.")

    # Show status chips
    st.caption("Latest statuses")
    for t in ("PFD_Package","Equipment_List","Utilities_Load"):
        rec = get_latest(project_id, t, phase_id)
        _status_chip(t, (rec or {}).get("status", "Missing"))
