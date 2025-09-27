import streamlit as st
from modules.unit_operations.pump import Pump
from modules.unit_operations.pipe import Pipe
from modules.unit_operations.separator import Separator

import graphviz
from fpdf import FPDF
import io
import datetime
import time

from artifact_registry import get_latest, save_artifact

# Try Firebase helpers; fall back to session memory
try:
    from firebase_db import save_project, load_all_projects
except Exception:
    def save_project(collection, doc_id, data):
        buf = st.session_state.setdefault("_legacy_sims", {})
        buf.setdefault(collection, {})
        buf[collection][doc_id] = {"data": data, "saved_at": time.time()}
        return {"key": f"{collection}__{doc_id}", "data": data}
    def load_all_projects(collection):
        buf = st.session_state.get("_legacy_sims", {}).get(collection, {})
        return [{"id": k, "data": v["data"]} for k, v in buf.items() if k != "_index"]


# === PDF Generator ===
def generate_pdf(units):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Process Flow Simulation Report", ln=True, align='C')
    pdf.ln(10)

    for unit in units:
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt=f"{unit.name} Outputs", ln=True)
        pdf.set_font("Arial", size=11)

        if isinstance(unit.outputs, dict) and "Outlet1" in unit.outputs:
            for outlet_name, data in unit.outputs.items():
                pdf.cell(200, 10, txt=f"{outlet_name}:", ln=True)
                for key, value in data.items():
                    if key == "composition" and isinstance(value, dict):
                        comp_text = ", ".join([f"{k}: {v}" for k, v in value.items()])
                        pdf.cell(200, 8, txt=f"  Composition: {comp_text}", ln=True)
                    else:
                        pdf.cell(200, 8, txt=f"  {key}: {value}", ln=True)
        else:
            for key, value in (unit.outputs or {}).items():
                if key == "composition" and isinstance(value, dict):
                    comp_text = ", ".join([f"{k}: {v}" for k, v in value.items()])
                    pdf.cell(200, 8, txt=f"  Composition: {comp_text}", ln=True)
                else:
                    pdf.cell(200, 8, txt=f"  {key}: {value}", ln=True)
        pdf.ln(5)

    return io.BytesIO(pdf.output(dest='S').encode('latin-1'))


# === Main App Function ===
def run(stage: str):
    st.title("🧪 Process Flow Simulation (Legacy)")

    # Project/phase IDs for Rev4
    project_id = st.session_state.get("current_project_id", "P-DEMO")
    phase_id   = st.session_state.get("current_phase_id", f"PH-{stage}")

    # Read Subsurface artifact (Reservoir_Profiles)
    rp   = get_latest(project_id, "Reservoir_Profiles", phase_id)
    comp = (rp or {}).get("data", {}).get("composition", {})
    cond = (rp or {}).get("data", {}).get("conditions", {})

    # --- normalize composition from Subsurface to dicts {component: z} ---
    def _to_z_map(obj, key_field="component", val_field="z"):
        if obj is None:
            return {}
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                try:
                    out[str(k)] = float(v)
                except Exception:
                    pass
            return out
        if isinstance(obj, list):
            out = {}
            for row in obj:
                if isinstance(row, dict):
                    k = row.get(key_field) or row.get("name") or row.get("comp")
                    v = row.get(val_field) or row.get("value") or row.get("fraction")
                    if k is not None and v is not None:
                        try:
                            out[str(k)] = float(v)
                        except Exception:
                            pass
            return out
        return {}

    comp_raw = comp or {}
    gas_z = _to_z_map(comp_raw.get("gas"))
    oil_z = _to_z_map(comp_raw.get("oil"))
    inj_z = _to_z_map(comp_raw.get("inj_gas"))
    comp = {"gas": gas_z, "oil": oil_z, "inj_gas": inj_z}

    # Defaults from conditions (best-effort)
    default_T = float(cond.get("reservoir_T_C", 60))   # °C
    default_P = float(cond.get("reservoir_P_bar", 20)) # bar

    # Component choices for UI
    default_components = list(gas_z.keys()) or ["Methane", "Ethane", "Propane", "Butane", "CO2", "H2S"]

    dot = graphviz.Digraph()

    if "process_units" not in st.session_state:
        st.session_state.process_units = []

    # === Sidebar: Add Equipment ===
    st.sidebar.header("Add Equipment")
    unit_type = st.sidebar.selectbox("Select Equipment Type", ["Pump", "Pipe", "Separator"], key="selected_unit_type")
    if st.sidebar.button("Add Unit"):
        uid = f"{unit_type}{len(st.session_state.process_units) + 1}"
        if unit_type == "Pump":
            st.session_state.process_units.append(Pump(uid))
        elif unit_type == "Pipe":
            st.session_state.process_units.append(Pipe(uid))
        elif unit_type == "Separator":
            st.session_state.process_units.append(Separator(uid))
    st.sidebar.write("Units so far:", [u.name for u in st.session_state.process_units])

    # === Load Past Simulations ===
    st.markdown("### 📂 Load Past Simulations")
    all_sims = load_all_projects("process_simulations")

    # Normalize to list of {"id": ..., "data": {...}}
    sims = []
    if isinstance(all_sims, list):
        sims = all_sims
    elif isinstance(all_sims, dict):
        sims = [{"id": k, "data": v} for k, v in all_sims.items()]

    if sims:
        labels = [f"🗓️ {s['data'].get('timestamp', s['id'])} — {s['id']}" for s in sims]
        selected_label = st.selectbox("Select a simulation to load", labels)
        if st.button("📥 Load Selected Simulation"):
            sel = sims[labels.index(selected_label)]
            sim_data = sel["data"]

            st.session_state.process_units = []
            for unit_info in sim_data.get("units", []):
                unit_type = unit_info.get("type")
                name = unit_info.get("name", unit_type)

                if unit_type == "Pump":
                    unit = Pump(name)
                elif unit_type == "Pipe":
                    unit = Pipe(name)
                elif unit_type == "Separator":
                    unit = Separator(name)
                else:
                    continue

                unit.inputs = unit_info.get("inputs", {}) or {}
                unit.outputs = unit_info.get("outputs", {}) or {}
                st.session_state.process_units.append(unit)

            st.success(f"✅ Loaded simulation: {selected_label}")
            st.session_state.simulate_now = True

    # === Inputs for Each Unit ===
    for unit in st.session_state.process_units:
        # ensure keys exist
        unit.inputs.setdefault("flowrate", 1000.0)
        unit.inputs.setdefault("pressure", default_P)
        unit.inputs.setdefault("temperature", default_T)
        unit.inputs.setdefault("composition", {"Methane": 1.0})

        with st.expander(f"{unit.name} - Inputs"):
            unit.inputs["flowrate"] = st.number_input(f"{unit.name} - Flowrate (kg/h)", value=float(unit.inputs["flowrate"]))
            unit.inputs["pressure"] = st.number_input(f"{unit.name} - Pressure (bar)", value=float(unit.inputs["pressure"]))
            unit.inputs["temperature"] = st.number_input(f"{unit.name} - Temperature (°C)", value=float(unit.inputs["temperature"]))

            if hasattr(unit, "split_ratio"):
                unit.split_ratio = st.slider(f"{unit.name} - Split Ratio (Outlet 1)", 0.0, 1.0, float(getattr(unit, "split_ratio", 0.5)))

            st.markdown(f"**{unit.name} - Select Components**")
            available_components = default_components
            selected_components = st.multiselect(
                f"Select components for {unit.name}",
                options=available_components,
                default=list((unit.inputs.get("composition") or {"Methane": 1.0}).keys()),
                key=f"{unit.name}_select"
            )

            comp_data = [
                {"Component": c, "Fraction": float((unit.inputs.get("composition") or {}).get(c, 0.0))}
                for c in selected_components
            ]
            comp_df = st.data_editor(comp_data, key=f"{unit.name}_composition")

            unit.inputs["composition"] = {
                row["Component"]: float(row["Fraction"])
                for row in comp_df if row["Component"] in selected_components
            }

            total_frac = sum(unit.inputs["composition"].values())
            if abs(total_frac - 1.0) > 0.01:
                st.warning(f"⚠️ {unit.name} - Total mole fraction = {total_frac:.3f} (should be 1.0)")

    # === Trigger Simulation ===
    if st.button("Simulate"):
        st.session_state.simulate_now = True

    # === Show Results ===
    if st.session_state.get("simulate_now"):
        st.subheader("🔄 Simulation Results")
        previous_output = None

        for idx, unit in enumerate(st.session_state.process_units):
            if idx != 0 and previous_output:
                unit.inputs["flowrate"] = previous_output.get("flowrate", unit.inputs["flowrate"])
                unit.inputs["pressure"] = previous_output.get("pressure", unit.inputs["pressure"])
                unit.inputs["temperature"] = previous_output.get("temperature", unit.inputs["temperature"])
                unit.inputs["composition"] = previous_output.get("composition", unit.inputs["composition"])

            unit.calculate()
            previous_output = unit.outputs

            st.write(f"**{unit.name} Outputs:**")
            if isinstance(unit.outputs, dict) and "Outlet1" in unit.outputs:
                st.write("➡️ Outlet 1:")
                st.json(unit.outputs["Outlet1"])
                st.write("➡️ Outlet 2:")
                st.json(unit.outputs["Outlet2"])
            else:
                st.json(unit.outputs)

        # === Flow Diagram ===
        with st.expander("🧭 Auto-Generated Flow Diagram"):
            for unit in st.session_state.process_units:
                dot.node(unit.name, shape="box")
            for i in range(len(st.session_state.process_units) - 1):
                dot.edge(st.session_state.process_units[i].name, st.session_state.process_units[i + 1].name)
            st.graphviz_chart(dot)

        # === PDF Export ===
        if isinstance(previous_output, dict):
            pdf_buffer = generate_pdf(st.session_state.process_units)
            st.download_button(
                label="📄 Download PDF Report",
                data=pdf_buffer,
                file_name="process_flow_simulation_report.pdf",
                mime="application/pdf"
            )

            # Save a copy of the run (cloud or session)
            sim_data = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "user": st.session_state.get("user", "guest"),
                "units": [{
                    "name": u.name,
                    "type": type(u).__name__,
                    "inputs": u.inputs,
                    "outputs": u.outputs
                } for u in st.session_state.process_units]
            }
            save_project("process_simulations", f"sim_{datetime.datetime.utcnow().timestamp()}", sim_data)
            st.success("✅ Simulation saved.")

        # --- Rev4 artifacts from legacy run ---
        # 1) Equipment_List
        equip_items = [{
            "tag": u.name,
            "type": type(u).__name__,
            "service": getattr(u, "service", ""),
        } for u in st.session_state.process_units]
        # Equipment_List
        # After simulation, aggregate utilities from all units
        heating_MW = sum(
            u.outputs.get("heating_MW", 0)
            for u in st.session_state.process_units
            if isinstance(u.outputs, dict)
        )
        electrical_MW = sum(
            u.outputs.get("electrical_MW", 0)
            for u in st.session_state.process_units
            if isinstance(u.outputs, dict)
        )

        save_artifact(project_id, phase_id, "Engineering", "Utilities_Load",
            {"origin": "simulation", "heating_MW": heating_MW, "electrical_MW": electrical_MW},
            status="Approved")
        # PFD_Package
        pkg = {
            "origin": "simulation",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "user": st.session_state.get("user", "guest"),
            "units": [  # list of unit operation summaries
                {
                    "name": u.name,
                    "type": type(u).__name__,
                    "inputs": u.inputs,
                    "outputs": u.outputs
                } for u in st.session_state.process_units
            ],
            "flow_diagram": dot.source,  # Graphviz DOT source (optional)
            "equipment_list": equip_items,  # already built above
            "conditions": cond,  # reservoir/process conditions if relevant
            # Add any other summary stats, e.g. total flow, total energy, etc.
        }




        st.success("Rev4 artifacts saved: Equipment_List, PFD_Package, Utilities_Load.")

        # === Reset Button ===
        if st.button("🔁 Reset Simulation"):
            st.session_state.process_units = []
            st.session_state.simulate_now = False
            st.rerun()
