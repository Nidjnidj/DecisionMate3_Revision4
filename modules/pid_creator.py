import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data
from graphviz import Digraph

def run(T):
    title = T.get("pid_creator_title", "P&ID Diagram Creator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("pid_creator", ""))

    st.subheader(T.get("equipment_input", "Define Equipment"))
    equipment = st.text_input(T.get("equipment_list", "Enter equipment (comma-separated)"),
                               placeholder="Pump-P101, Separator-S101, Heater-H101")

    st.subheader(T.get("instrumentation_input", "Define Instrumentation"))
    instruments = st.text_input(T.get("instrument_list", "Enter instruments (comma-separated)"),
                                 placeholder="Pressure Sensor-PI101, Flow Transmitter-FT101")

    st.subheader(T.get("connection_input", "Define Connections"))
    connections = st.text_area(T.get("connections", "Define connections (format: From->To)"),
                               placeholder="Pump-P101->Heater-H101\nHeater-H101->Separator-S101")

    if st.button(T.get("generate_diagram", "Generate Diagram")) and equipment:
        equipment_list = [e.strip() for e in equipment.split(',') if e.strip()]
        instrument_list = [i.strip() for i in instruments.split(',') if i.strip()]
        connection_list = [c.strip() for c in connections.splitlines() if '->' in c]

        dot = Digraph()
        for eq in equipment_list:
            dot.node(eq, shape="box")

        for inst in instrument_list:
            dot.node(inst, shape="ellipse")

        for conn in connection_list:
            try:
                src, tgt = conn.split('->')
                dot.edge(src.strip(), tgt.strip())
            except:
                continue

        st.graphviz_chart(dot)

        df_eq = pd.DataFrame({"Equipment": equipment_list})
        df_inst = pd.DataFrame({"Instruments": instrument_list})

        st.subheader(T.get("summary", "Summary Tables"))
        st.markdown("**" + T.get("equipment", "Equipment") + "**")
        st.dataframe(df_eq)
        st.markdown("**" + T.get("instrumentation", "Instrumentation") + "**")
        st.dataframe(df_inst)

        # === Excel Export ===
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
            df_eq.to_excel(writer, sheet_name="Equipment", index=False)
            df_inst.to_excel(writer, sheet_name="Instruments", index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="pid_elements.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === PDF Export ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for e in equipment_list:
            pdf.cell(200, 10, txt=f"Equipment: {e}", ln=True)
        for i in instrument_list:
            pdf.cell(200, 10, txt=f"Instrument: {i}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="pid_elements.pdf", mime="application/pdf")

        # === Firebase Save/Load ===
        if st.button(T.get("save", "Save")):
            data = {
                "equipment": equipment_list,
                "instruments": instrument_list,
                "connections": connection_list
            }
            save_project(st.session_state.username, title, data)
            st.success(T.get("save_success", "Project saved successfully."))

        if st.button(T.get("load", "Load")):
            loaded = load_project_data(st.session_state.username, title)
            if loaded:
                st.json(loaded)
            else:
                st.warning(T.get("load_warning", "No saved data found."))
    else:
        st.info(T.get("waiting_input", "Please enter equipment and optionally instruments/connections."))

pid_creator = run
