import streamlit as st
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T.get("mixer_splitter_title", "Mixer & Splitter Tool"))
    st.markdown(T.get("descriptions", {}).get("mixer_splitter_title", ""))

    st.subheader(T.get("mixer_section", "Mixer"))
    flow1 = st.number_input(T.get("flow_stream_1", "Flowrate of Stream 1 (kg/h)"), min_value=0.0, value=100.0)
    conc1 = st.number_input(T.get("conc_stream_1", "Concentration of Stream 1 (%)"), min_value=0.0, max_value=100.0, value=20.0)

    flow2 = st.number_input(T.get("flow_stream_2", "Flowrate of Stream 2 (kg/h)"), min_value=0.0, value=150.0)
    conc2 = st.number_input(T.get("conc_stream_2", "Concentration of Stream 2 (%)"), min_value=0.0, max_value=100.0, value=40.0)

    total_flow = flow1 + flow2
    if total_flow > 0:
        mixed_conc = (flow1 * conc1 + flow2 * conc2) / total_flow
    else:
        mixed_conc = 0.0

    st.success(f"{T.get('mixed_flow', 'Mixed Flowrate')}: {total_flow:.2f} kg/h")
    st.success(f"{T.get('mixed_concentration', 'Mixed Concentration')}: {mixed_conc:.2f} %")

    st.subheader(T.get("splitter_section", "Splitter"))
    split_ratio = st.slider(T.get("split_ratio", "Split Ratio (Stream A %)"), 0, 100, 50)

    flow_a = total_flow * (split_ratio / 100)
    flow_b = total_flow - flow_a

    st.success(f"{T.get('stream_a_flow', 'Stream A Flowrate')}: {flow_a:.2f} kg/h")
    st.success(f"{T.get('stream_b_flow', 'Stream B Flowrate')}: {flow_b:.2f} kg/h")
    st.success(f"{T.get('concentration_all', 'Concentration for All Outputs')}: {mixed_conc:.2f} %")

    if st.button(T.get("save", "Save")):
        save_project(st.session_state.username, T.get("mixer_splitter_title", "Mixer & Splitter Tool"), {
            "flow1": flow1, "conc1": conc1,
            "flow2": flow2, "conc2": conc2,
            "total_flow": total_flow, "mixed_conc": mixed_conc,
            "split_ratio": split_ratio,
            "flow_a": flow_a, "flow_b": flow_b
        })
        st.success(T.get("save_success", "Saved successfully."))

    if st.button(T.get("load", "Load")):
        data = load_project_data(st.session_state.username, T.get("mixer_splitter_title", "Mixer & Splitter Tool"))
        if data:
            st.json(data)
        else:
            st.warning(T.get("load_warning", "No saved data found."))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=T.get("mixer_splitter_title", "Mixer & Splitter Tool"), ln=True)
    pdf.multi_cell(0, 10, txt=f"""
Stream 1: {flow1} kg/h, {conc1} %
Stream 2: {flow2} kg/h, {conc2} %
Mixed Flow: {total_flow:.2f} kg/h
Mixed Conc.: {mixed_conc:.2f} %
Split Ratio: {split_ratio}%
Stream A: {flow_a:.2f} kg/h
Stream B: {flow_b:.2f} kg/h
""")
    pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
    st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output, file_name="mixer_splitter_result.pdf", mime="application/pdf")

# Important for app.py to recognize
mixer_splitter = run
