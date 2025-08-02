import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data
from graphviz import Digraph

def run(T):
    title = T.get("pfd_creator_title", "Process Flow Diagram (PFD) Creator")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("pfd_creator", ""))

    st.subheader(T.get("add_elements", "Add Process Elements"))

    components = st.text_input(T.get("component_list", "Enter components (comma-separated)"),
                               placeholder="Pump-101, Heater-201, Separator-301, Cooler-401")
    connections = st.text_area(T.get("connections", "Define connections (format: From->To)"),
                               placeholder="Pump-101->Heater-201\nHeater-201->Separator-301\nSeparator-301->Cooler-401")

    if st.button(T.get("generate_diagram", "Generate Diagram")) and components and connections:
        component_list = [x.strip() for x in components.split(',')]
        connection_list = [x.strip() for x in connections.splitlines() if '->' in x]

        dot = Digraph()
        for comp in component_list:
            dot.node(comp)

        for conn in connection_list:
            try:
                src, tgt = conn.split('->')
                dot.edge(src.strip(), tgt.strip())
            except:
                continue

        st.graphviz_chart(dot)

        # === Dataframe summary ===
        df = pd.DataFrame({
            "Component": component_list
        })

        st.subheader(T.get("component_table", "Component Summary Table"))
        st.dataframe(df)

        # === Export Excel ===
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="pfd_components.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # === Export PDF ===
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for comp in component_list:
            pdf.cell(200, 10, txt=f"Component: {comp}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="pfd_components.pdf", mime="application/pdf")

        # === Save to Firebase ===
        if st.button(T.get("save", "Save")):
            data = {
                "components": component_list,
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
        st.info(T.get("waiting_input", "Enter components and connections to build the diagram."))

pfd_creator = run
