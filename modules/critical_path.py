import streamlit as st
import pandas as pd
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data
import networkx as nx

def run(T):
    title = T.get("critical_path_title", "Critical Path Analyzer")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("critical_path", ""))

    if "cpm_data" not in st.session_state:
        st.session_state.cpm_data = []

    st.subheader(T.get("activity_input", "Add Project Activity"))
    name = st.text_input(T.get("activity_name", "Activity Name"))
    duration = st.number_input(T.get("activity_duration", "Duration (days)"), min_value=1, max_value=365, step=1)
    dependencies = st.text_input(T.get("dependencies", "Dependencies (comma-separated)"))

    if st.button(T.get("add_activity", "Add Activity")) and name:
        st.session_state.cpm_data.append({
            "Activity": name.strip(),
            "Duration": duration,
            "Dependencies": [d.strip() for d in dependencies.split(",") if d.strip()]
        })

    df = pd.DataFrame(st.session_state.cpm_data)
    if not df.empty:
        st.subheader(T.get("activity_table", "Activity Table"))
        st.dataframe(df)

        # Build network graph
        G = nx.DiGraph()
        for index, row in df.iterrows():
            G.add_node(row["Activity"], duration=row["Duration"])
            for dep in row["Dependencies"]:
                G.add_edge(dep, row["Activity"])

        try:
            topological_order = list(nx.topological_sort(G))
        except:
            st.error(T.get("cycle_error", "Cycle detected in dependencies. Check inputs."))
            return

        early_start = {}
        early_finish = {}

        for node in topological_order:
            preds = list(G.predecessors(node))
            if preds:
                early_start[node] = max(early_finish[p] for p in preds)
            else:
                early_start[node] = 0
            early_finish[node] = early_start[node] + G.nodes[node]["duration"]

        late_finish = {}
        late_start = {}

        reversed_order = reversed(topological_order)
        max_finish_time = max(early_finish.values())

        for node in reversed_order:
            succs = list(G.successors(node))
            if succs:
                late_finish[node] = min(late_start[s] for s in succs)
            else:
                late_finish[node] = max_finish_time
            late_start[node] = late_finish[node] - G.nodes[node]["duration"]

        critical_path = [node for node in G.nodes if early_start[node] == late_start[node]]

        results = []
        for node in G.nodes:
            results.append({
                "Activity": node,
                "Duration": G.nodes[node]["duration"],
                "ES": early_start[node],
                "EF": early_finish[node],
                "LS": late_start[node],
                "LF": late_finish[node],
                "Slack": late_start[node] - early_start[node],
                "Critical": "Yes" if node in critical_path else "No"
            })

        result_df = pd.DataFrame(results).sort_values("ES").reset_index(drop=True)
        st.success(T.get("critical_path_result", "Critical Path Identified"))
        st.dataframe(result_df)

        # Excel Export
        towrite = io.BytesIO()
        result_df.to_excel(towrite, index=False)
        towrite.seek(0)
        st.download_button(label=T.get("download_excel", "Download Excel"), data=towrite,
                           file_name="critical_path.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # PDF Export
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=title, ln=True)
        for _, row in result_df.iterrows():
            pdf.cell(200, 10, txt=f"{row['Activity']} | Slack: {row['Slack']} | Critical: {row['Critical']}", ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(label=T.get("download_pdf", "Download PDF"), data=pdf_output,
                           file_name="critical_path.pdf", mime="application/pdf")

        # Firebase Save
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.cpm_data)
            st.success(T.get("save_success", "Data saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.cpm_data = data
                st.success(T.get("load_success", "Data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

critical_path = run
