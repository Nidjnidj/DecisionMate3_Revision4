# workflows/workspace_arch_construction.py
from __future__ import annotations
import streamlit as st
from datetime import datetime

# artifact registry (uses Firestore if configured; in-memory otherwise)
from artifact_registry import save_artifact, get_latest

def _initial_status():
    mode = st.session_state.get("CASCADE_MODE", "manual")
    return "Approved" if mode == "auto" else "Pending"

def run():
    st.header("🏛️ Architecture & Construction — Workspace")

    kind = st.selectbox("Project type", ["Building / Civil", "Industrial"], key="ac_kind")

    # Tabs: Design → BOM → Schedule → Cost
    t1, t2, t3, t4 = st.tabs(["Design", "BOM", "Schedule", "Cost"])

    project_id = st.session_state.get("current_project_id", "P-AC-DEMO")
    phase_id   = st.session_state.get("current_phase_id", "PH-FEL1")

    # ---------- 1) DESIGN ----------
    with t1:
        st.caption("Quick parametric inputs (simple scaffolding).")

        if kind == "Building / Civil":
            colA, colB, colC = st.columns(3)
            with colA:
                floors = st.number_input("Floors", 1, 60, 5)
            with colB:
                gross_area = st.number_input("Gross floor area (m²)", 50.0, step=10.0, value=1200.0)
            with colC:
                occupancy = st.selectbox("Building type", ["Residential", "Office", "School", "Hospital"], index=1)

            colU1, colU2, colU3 = st.columns(3)
            with colU1:
                electrical_load_kw = st.number_input("Estimated electrical load (kW)", 10.0, step=5.0, value=320.0)
            with colU2:
                water_demand_m3d = st.number_input("Water demand (m³/day)", 1.0, step=1.0, value=130.0)
            with colU3:
                sewage_m3d = st.number_input("Sewage (m³/day)", 1.0, step=1.0, value=115.0)

            design_payload = {
                "type": "civil",
                "floors": floors,
                "gross_area_m2": gross_area,
                "occupancy": occupancy,
                "electrical_load_kw": electrical_load_kw,
                "water_demand_m3d": water_demand_m3d,
                "sewage_m3d": sewage_m3d,
            }
            utilities_payload = {
                "electrical_circuits": int(max(10, electrical_load_kw // 5)),
                "plumbing_lines": int(max(10, gross_area // 50)),
                "sewage_lines": int(max(10, gross_area // 60)),
                "cable_length_m": int(gross_area * 1.2),
                "piping_length_m": int(gross_area * 0.8),
            }

        else:  # Industrial
            colA, colB, colC = st.columns(3)
            with colA:
                plot_area = st.number_input("Plot area (m²)", 200.0, step=10.0, value=6000.0)
            with colB:
                process_units = st.number_input("Process units (count)", 1, 100, 4)
            with colC:
                pipe_classes = st.multiselect("Pipe classes", ["CS150", "CS300", "SS150", "SS300"], default=["CS150", "SS150"])

            design_payload = {
                "type": "industrial",
                "plot_area_m2": plot_area,
                "process_units": process_units,
                "pipe_classes": pipe_classes,
            }
            utilities_payload = {
                "pipe_runs": int(process_units * 8),
                "avg_pipe_od_in": 6,
                "approx_cable_tray_m": int(process_units * 50),
            }

        # --- Quick required artifacts (Draft) ---
        st.markdown("#### Quick required artifacts")

        # Light payloads that reuse current inputs
        program_brief_payload = {
            "title": "Program Brief",
            "summary": f"Auto-generated brief for {kind} project.",
            "inputs_snapshot": design_payload,
        }
        site_screener_payload = {
            "title": "Site Screener",
            "notes": "Quick screener draft from current inputs.",
            "candidates": [
                {"name": "Site A", "score": 0.6},
                {"name": "Site B", "score": 0.5},
            ],
            "inputs_snapshot": design_payload,
        }
        concept_design_payload = {
            "title": "Concept Design Kit",
            "kit_version": "v0.1",
            "includes": ["footprint", "utilities", "envelope"],
            "design_snapshot": design_payload,
            "utilities_snapshot": utilities_payload,
        }

        c_pb, c_ss, c_cdk = st.columns(3)
        with c_pb:
            if st.button("Save Program_Brief (Draft)", key="btn_pb_draft"):
                save_artifact(project_id, phase_id, "Planning", "Program_Brief",
                              program_brief_payload, status="Draft")
                st.success("Program_Brief saved (Draft).")
        with c_ss:
            if st.button("Save Site_Screener (Draft)", key="btn_ss_draft"):
                save_artifact(project_id, phase_id, "Site", "Site_Screener",
                              site_screener_payload, status="Draft")
                st.success("Site_Screener saved (Draft).")
        with c_cdk:
            if st.button("Save Concept_Design_Kit (Draft)", key="btn_cdk_draft"):
                save_artifact(project_id, phase_id, "Design", "Concept_Design_Kit",
                              concept_design_payload, status="Draft")
                st.success("Concept_Design_Kit saved (Draft).")

        st.caption("Drafts appear under **Required Artifacts** as 'Draft/Pending' until approved.")

        # Existing design/utility saves
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save Construction_Design (Draft)"):
                save_artifact(project_id, phase_id, "Engineering", "Construction_Design",
                              design_payload, status="Draft")
                st.success("Design saved (Draft).")
        with c2:
            if st.button("Save Utilities_Layout (Draft)"):
                save_artifact(project_id, phase_id, "Engineering", "Utilities_Layout",
                              utilities_payload, status="Draft")
                st.success("Utilities layout saved (Draft).")

        # Optional: quick Risk Register draft
        with st.expander("Risk (quick draft)"):
            risk_payload = {
                "items": [
                    {"risk": "Design changes", "likelihood": 3, "impact": 3},
                    {"risk": "Permit delay",   "likelihood": 2, "impact": 4},
                ]
            }
            if st.button("Save Risk_Register (Draft)", key="btn_rr_draft"):
                save_artifact(project_id, phase_id, "Risk", "Risk_Register",
                              risk_payload, status="Draft")
                st.success("Risk_Register saved (Draft).")

    # ---------- 2) BOM ----------
    with t2:
        st.caption("Auto-generate a simple Bill of Materials from the design inputs.")
        design = get_latest(project_id, "Construction_Design", phase_id)
        utils  = get_latest(project_id, "Utilities_Layout", phase_id)

        if not design or not utils:
            st.warning("Save Design and Utilities first.")
        else:
            d = design.get("data", {})
            u = utils.get("data", {})

            items = []
            if d.get("type") == "civil":
                area = float(d.get("gross_area_m2", 0))
                floors = int(d.get("floors", 1))
                items += [
                    {"item": "Concrete (m³)",     "qty": round(area * floors * 0.12, 1)},
                    {"item": "Rebar (t)",         "qty": round(area * floors * 0.015, 2)},
                    {"item": "Brick/Block (m²)",  "qty": round(area * floors * 1.1, 1)},
                    {"item": "Cables (m)",        "qty": int(u.get("cable_length_m", 0))},
                    {"item": "Plumbing (m)",      "qty": int(u.get("piping_length_m", 0))},
                    {"item": "Sewer lines (m)",   "qty": int(u.get("sewage_lines", 0) * 10)},
                ]
            else:
                units = int(d.get("process_units", 0))
                pipe_runs = int(u.get("pipe_runs", 0))
                tray_m = int(u.get("approx_cable_tray_m", 0))
                items += [
                    {"item": "Structural steel (t)", "qty": round(units * 25.0, 1)},
                    {"item": "Pipe (m)",             "qty": pipe_runs * 100},
                    {"item": "Valves (ea)",          "qty": int(pipe_runs * 6)},
                    {"item": "Cable tray (m)",       "qty": tray_m},
                    {"item": "Instrumentation (ea)", "qty": int(units * 20)},
                ]

            st.write(items)
            if st.button("Save Bill_Of_Materials"):
                save_artifact(project_id, phase_id, "Procurement", "Bill_Of_Materials",
                              {"items": items}, status=_initial_status())
                st.success("BOM saved.")

    # ---------- 3) SCHEDULE ----------
    with t3:
        st.caption("Seed WBS + Schedule from BOM (very simple).")
        bom = get_latest(project_id, "Bill_Of_Materials", phase_id)
        if not bom:
            st.warning("Create a BOM first.")
        else:
            if st.button("Seed WBS + Schedule from BOM"):
                nodes = [{"id": "1", "parent": None, "name": "Construction Project",
                          "type": "Project", "phase": "FEL", "owner": "PM"}]
                activities = []
                for i, it in enumerate(bom.get("data", {}).get("items", []), start=1):
                    aid = f"A{i}"
                    nodes.append({"id": f"1.{i}", "parent": "1", "name": it["item"],
                                  "type": "WP", "phase": "FEL", "owner": "Construction"})
                    activities.append({"id": aid, "name": f"Install {it['item']}",
                                       "wbs_id": f"1.{i}", "dur_days": max(5, int(it.get("qty", 1) // 10)),
                                       "predecessors": []})
                save_artifact(project_id, phase_id, "Schedule", "WBS",
                              {"nodes": nodes}, status=_initial_status(), sources=["BOM@seed"])
                save_artifact(project_id, phase_id, "Schedule", "Schedule_Network", {
                    "activities": activities,
                    "critical_path_ids": [a["id"] for a in activities[:3]],
                    "start_date": "2026-03-01",
                    "finish_date": "2026-06-30",
                }, status=_initial_status(), sources=["BOM@seed"])
                st.success("WBS & Schedule seeded.")

    # ---------- 4) COST ----------
    with t4:
        st.caption("Create a cost model from BOM with unit rates.")
        bom = get_latest(project_id, "Bill_Of_Materials", phase_id)
        if not bom:
            st.warning("Create a BOM first.")
        else:
            rates = {
                "Concrete (m³)": 120.0,
                "Rebar (t)": 850.0,
                "Brick/Block (m²)": 25.0,
                "Cables (m)": 2.5,
                "Plumbing (m)": 3.0,
                "Sewer lines (m)": 2.0,
                "Structural steel (t)": 980.0,
                "Pipe (m)": 12.0,
                "Valves (ea)": 150.0,
                "Cable tray (m)": 8.0,
                "Instrumentation (ea)": 300.0,
            }
            line_items = []
            total = 0.0
            for it in bom.get("data", {}).get("items", []):
                rate = rates.get(it["item"], 1.0)
                cost = float(it.get("qty", 0)) * rate
                line_items.append({"item": it["item"], "qty": it["qty"], "rate": rate, "cost": round(cost, 2)})
                total += cost
            st.write(line_items)
            st.metric("Estimated CAPEX", f"{total:,.0f}")
            if st.button("Save Cost_Model"):
                save_artifact(
                    project_id,
                    phase_id,
                    "Finance",
                    "Cost_Model",
                    {"items": line_items, "total": total, "ts": datetime.utcnow().isoformat()},
                    status=_initial_status(),
                    sources=["BOM@rates"],
                )
                st.success("Cost model saved.")
