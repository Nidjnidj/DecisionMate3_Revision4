# 📅 P6-Style Project Scheduler for DecisionMate (Full Professional Version)
def run(T):
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    import networkx as nx
    from pyvis.network import Network
    import io
    from fpdf import FPDF
    import streamlit.components.v1 as components
    from firebase_db import save_project, load_project_data

    st.set_page_config(page_title="P6-Style Scheduler", layout="wide")
    st.title("📅 P6-Style Project Scheduler")
    st.caption("A comprehensive scheduling module inspired by Primavera P6")

    for key in ["p6_activities", "p6_dependencies", "p6_baseline"]:
        if key not in st.session_state:
            st.session_state[key] = [] if key != "p6_baseline" else None

    def compute_advanced_cpm(activities, dependencies):
        G = nx.DiGraph()
        act_map = {a['id']: a for a in activities}
        for act in activities:
            G.add_node(act['id'], duration=act['duration'])
        for dep in dependencies:
            pred = dep['pred'].split("(")[-1].strip(")")
            succ = dep['succ'].split("(")[-1].strip(")")
            lag = dep['lag']
            G.add_edge(pred, succ, type=dep['type'], lag=lag)
        try:
            order = list(nx.topological_sort(G))
        except:
            return [], "Cycle detected in schedule."
        es, ef = {}, {}
        for node in order:
            preds = list(G.predecessors(node))
            max_time = 0
            for p in preds:
                p_ef = ef[p]
                lag = G.edges[p, node]['lag']
                link_type = G.edges[p, node]['type']
                if link_type == 'FS':
                    max_time = max(max_time, p_ef + lag)
                elif link_type == 'SS':
                    max_time = max(max_time, es[p] + lag)
                elif link_type == 'FF':
                    max_time = max(max_time, p_ef + lag - act_map[node]['duration'])
                elif link_type == 'SF':
                    max_time = max(max_time, es[p] + lag - act_map[node]['duration'])
            es[node] = max_time
            ef[node] = es[node] + act_map[node]['duration']
        lf, ls = {}, {}
        max_finish = max(ef.values())
        for node in reversed(order):
            succs = list(G.successors(node))
            min_lf = max_finish
            for s in succs:
                s_ls = ls[s]
                lag = G.edges[node, s]['lag']
                link_type = G.edges[node, s]['type']
                if link_type == 'FS':
                    min_lf = min(min_lf, s_ls - lag)
                elif link_type == 'SS':
                    min_lf = min(min_lf, es[s] - lag)
                elif link_type == 'FF':
                    min_lf = min(min_lf, ef[s] - lag)
                elif link_type == 'SF':
                    min_lf = min(min_lf, s_ls + lag)
            lf[node] = min_lf
            ls[node] = lf[node] - act_map[node]['duration']
        result = []
        for node in order:
            float_val = ls[node] - es[node]
            result.append({
                "id": node,
                "name": act_map[node]['name'],
                "ES": es[node], "EF": ef[node],
                "LS": ls[node], "LF": lf[node],
                "Float": float_val,
                "Critical": float_val == 0
            })
        return result, None

    tabs = st.tabs(["Activities", "Dependencies", "Gantt Chart", "Network", "Dashboard", "Save/Load", "Export"])

    with tabs[0]:
        st.subheader("📋 Define Activities")
        with st.form("activity_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Activity Name")
                duration = st.number_input("Duration (days)", min_value=1, value=5)
                start = st.date_input("Planned Start")
            with col2:
                resource = st.text_input("Assigned Resource")
                progress = st.slider("% Complete", 0, 100, 0)
                wbs = st.text_input("WBS Code")
            with col3:
                actual_start = st.date_input("Actual Start")
                actual_finish = st.date_input("Actual Finish")
                remaining = st.number_input("Remaining Duration", min_value=0, value=0)
            submitted = st.form_submit_button("Add Activity")
            if submitted:
                st.session_state.p6_activities.append({
                    "id": name[:3].upper() + str(len(st.session_state.p6_activities)+1),
                    "name": name,
                    "duration": duration,
                    "start": start,
                    "wbs": wbs,
                    "resource": resource,
                    "progress": progress,
                    "actual_start": actual_start,
                    "actual_finish": actual_finish,
                    "remaining": remaining
                })
        if st.session_state.p6_activities:
            st.dataframe(pd.DataFrame(st.session_state.p6_activities))

    with tabs[1]:
        st.subheader("🔗 Define Dependencies")
        ids = [f"{a['name']} ({a['id']})" for a in st.session_state.p6_activities]
        with st.form("dependency_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                pred = st.selectbox("Predecessor", ids)
            with col2:
                succ = st.selectbox("Successor", ids)
            with col3:
                link_type = st.selectbox("Link Type", ["FS", "SS", "FF", "SF"])
                lag = st.number_input("Lag (days)", value=0)
            if st.form_submit_button("Add Link"):
                st.session_state.p6_dependencies.append({
                    "pred": pred,
                    "succ": succ,
                    "type": link_type,
                    "lag": lag
                })
        if st.session_state.p6_dependencies:
            st.dataframe(pd.DataFrame(st.session_state.p6_dependencies))

    with tabs[2]:
        st.subheader("📊 Gantt Chart")
        if st.session_state.p6_activities:
            df = pd.DataFrame(st.session_state.p6_activities)
            df["Start"] = pd.to_datetime(df["start"])
            df["Finish"] = df["Start"] + pd.to_timedelta(df["duration"], unit="D")
            df["ID"] = df["id"]
            cpm_data, err = compute_advanced_cpm(st.session_state.p6_activities, st.session_state.p6_dependencies)
            if err:
                st.error(err)
            else:
                critical_ids = [x['id'] for x in cpm_data if x['Critical']]
                float_map = {x['id']: x['Float'] for x in cpm_data}
                fig = go.Figure()
                for _, row in df.iterrows():
                    fig.add_trace(go.Bar(
                        x=[(row["Finish"] - row["Start"]).days],
                        y=[row["name"]],
                        base=row["Start"],
                        orientation='h',
                        marker=dict(color='red' if row["ID"] in critical_ids else 'blue'),
                        name=row["id"],
                        hovertext=f"{row['progress']}% | Float: {float_map.get(row['ID'], '?')}"
                    ))
                fig.update_layout(barmode="overlay", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(pd.DataFrame(cpm_data))

    with tabs[3]:
        st.subheader("📌 Network Diagram")
        if st.session_state.p6_activities:
            G = nx.DiGraph()
            for act in st.session_state.p6_activities:
                G.add_node(act["id"], label=f"{act['name']}\n{act['duration']}d")
            for dep in st.session_state.p6_dependencies:
                pred_id = dep["pred"].split("(")[-1].strip(")")
                succ_id = dep["succ"].split("(")[-1].strip(")")
                G.add_edge(pred_id, succ_id, label=f"{dep['type']}+{dep['lag']}")
            net = Network(height="600px", width="100%", directed=True)
            net.from_nx(G)
            net.save_graph("p6_network.html")
            with open("p6_network.html", "r", encoding="utf-8") as f:
                components.html(f.read(), height=600)

    with tabs[4]:
        st.subheader("📈 Dashboard KPIs")
        if st.session_state.p6_activities:
            df = pd.DataFrame(st.session_state.p6_activities)
            st.metric("Total Activities", len(df))
            st.metric("% Complete", f"{round(df['progress'].mean(), 1)}%")
            st.metric("Critical Tasks", df[df['duration'] == df['duration'].max()].shape[0])

    with tabs[5]:
        st.subheader("💾 Save / Load")
        project_name = st.text_input("Project ID", value="MyP6Project")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save to Firebase"):
                data = {
                    "activities": st.session_state.p6_activities,
                    "dependencies": st.session_state.p6_dependencies,
                    "baseline": st.session_state.p6_baseline
                }
                save_project(st.session_state.username, project_name, data)
                st.success("Project saved.")
        with col2:
            if st.button("Load from Firebase"):
                data = load_project_data(st.session_state.username, project_name)
                if data:
                    st.session_state.p6_activities = data.get("activities", [])
                    st.session_state.p6_dependencies = data.get("dependencies", [])
                    st.session_state.p6_baseline = data.get("baseline", None)
                    st.success("Loaded.")

    with tabs[6]:
        st.subheader("📤 Export Report")
        if st.session_state.p6_activities:
            df = pd.DataFrame(st.session_state.p6_activities)
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False)
            st.download_button("⬇️ Download Excel", data=towrite.getvalue(), file_name="p6_schedule.xlsx")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Project Schedule", ln=True)
            for _, row in df.iterrows():
                pdf.cell(200, 10, txt=f"{row['name']}: {row['start']} +{row['duration']}d | {row['progress']}%", ln=True)
            pdf_out = io.BytesIO()
            pdf.output(pdf_out)
            st.download_button("📄 Download PDF", data=pdf_out.getvalue(), file_name="p6_schedule.pdf")
