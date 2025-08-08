import streamlit as st
from modules.unit_operations.pump import Pump
from modules.unit_operations.pipe import Pipe
from modules.unit_operations.separator import Separator
from firebase_db import save_project, load_all_projects
import graphviz
from fpdf import FPDF
import io
import datetime

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
                    if key == "composition":
                        comp_text = ", ".join([f"{k}: {v}" for k, v in value.items()])
                        pdf.cell(200, 8, txt=f"  Composition: {comp_text}", ln=True)
                    else:
                        pdf.cell(200, 8, txt=f"  {key}: {value}", ln=True)
        else:
            for key, value in unit.outputs.items():
                if key == "composition":
                    comp_text = ", ".join([f"{k}: {v}" for k, v in value.items()])
                    pdf.cell(200, 8, txt=f"  Composition: {comp_text}", ln=True)
                else:
                    pdf.cell(200, 8, txt=f"  {key}: {value}", ln=True)
        pdf.ln(5)

    return io.BytesIO(pdf.output(dest='S').encode('latin-1'))


# === Main App Function ===
def run(T):
    st.title("🧪 Process Flow Simulation")
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

    if all_sims:
        dropdown_options = {
            f"🗓️ {data.get('timestamp', key)}": key
            for key, data in all_sims.items()
        }

        selected_label = st.selectbox("Select a simulation to load", list(dropdown_options.keys()))
        selected_sim = dropdown_options[selected_label]

        if st.button("📥 Load Selected Simulation"):
            sim_data = all_sims[selected_sim]
            st.session_state.process_units = []

            for unit_info in sim_data["units"]:
                unit_type = unit_info["type"]
                name = unit_info["name"]

                if unit_type == "Pump":
                    unit = Pump(name)
                elif unit_type == "Pipe":
                    unit = Pipe(name)
                elif unit_type == "Separator":
                    unit = Separator(name)
                else:
                    continue

                unit.inputs = unit_info["inputs"]
                unit.outputs = unit_info["outputs"]
                st.session_state.process_units.append(unit)

            st.success(f"✅ Loaded simulation: {selected_label}")
            st.session_state.simulate_now = True

    # === Inputs for Each Unit ===
    for unit in st.session_state.process_units:
        with st.expander(f"{unit.name} - Inputs"):
            unit.inputs["flowrate"] = st.number_input(f"{unit.name} - Flowrate (kg/h)", value=unit.inputs["flowrate"])
            unit.inputs["pressure"] = st.number_input(f"{unit.name} - Pressure (bar)", value=unit.inputs["pressure"])
            unit.inputs["temperature"] = st.number_input(f"{unit.name} - Temperature (°C)", value=unit.inputs["temperature"])

            if hasattr(unit, "split_ratio"):
                unit.split_ratio = st.slider(f"{unit.name} - Split Ratio (Outlet 1)", 0.0, 1.0, unit.split_ratio)

            st.markdown(f"**{unit.name} - Select Components**")
            available_components = ["Methane", "Ethane", "Propane", "Butane", "CO2", "H2S"]
            selected_components = st.multiselect(
                f"Select components for {unit.name}",
                options=available_components,
                default=list(unit.inputs.get("composition", {"Methane": 1.0}).keys()),
                key=f"{unit.name}_select"
            )

            comp_data = [
                {"Component": comp, "Fraction": unit.inputs.get("composition", {}).get(comp, 0.0)}
                for comp in selected_components
            ]
            comp_df = st.data_editor(comp_data, key=f"{unit.name}_composition")

            unit.inputs["composition"] = {
                row["Component"]: row["Fraction"]
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
                unit.inputs["flowrate"] = previous_output.get("flowrate", 0)
                unit.inputs["pressure"] = previous_output.get("pressure", 0)
                unit.inputs["temperature"] = previous_output.get("temperature", 0)
                unit.inputs["composition"] = previous_output.get("composition", {"Methane": 1.0})

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

            # === Save to Firebase ===
            sim_data = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "user": st.session_state.get("user", "guest"),
                "units": []
            }

            for unit in st.session_state.process_units:
                sim_data["units"].append({
                    "name": unit.name,
                    "type": type(unit).__name__,
                    "inputs": unit.inputs,
                    "outputs": unit.outputs
                })

            save_project("process_simulations", f"sim_{datetime.datetime.utcnow().timestamp()}", sim_data)
            st.success("✅ Simulation saved to cloud.")

        # === Reset Button ===
        if st.button("🔁 Reset Simulation"):
            st.session_state.process_units = []
            st.session_state.simulate_now = False
            st.rerun()
