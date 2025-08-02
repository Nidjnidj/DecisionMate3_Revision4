import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from fpdf import FPDF
from firebase_db import save_project, load_project_data

def run(T):
    st.header(T.get("equipment_comparison_title", "Equipment Comparison Tool"))
    st.markdown(T.get("descriptions", {}).get("equipment_comparison", ""))

    criteria = [
        T.get("size", "Size"),
        T.get("power", "Power"),
        T.get("emissions", "Emissions"),
        T.get("capex", "CAPEX"),
        T.get("opex", "OPEX")
    ]

    st.subheader(T.get("criteria_weights", "Criteria Weights (Total = 100%)"))
    weights = {}
    for crit in criteria:
        weights[crit] = st.slider(f"{crit} (%)", 0, 100, 20)

    if sum(weights.values()) != 100:
        st.warning(T.get("weight_warning", "Total weight must equal 100%."))
        return

    st.subheader(T.get("equipment_data", "Enter Equipment Data"))
    num_equipment = st.number_input(T.get("num_equipment", "Number of Equipment Options"), min_value=1, value=3)
    data = []
    for i in range(int(num_equipment)):
        st.markdown(f"**{T.get('equipment', 'Equipment')} {i+1}**")
        name = st.text_input(f"{T.get('name', 'Name')} {i+1}", key=f"name_{i}")
        row = {"Name": name}
        for crit in criteria:
            row[crit] = st.number_input(f"{crit} for {name}", key=f"{crit}_{i}")
        data.append(row)

    if st.button(T.get("compare", "Compare")):
        df = pd.DataFrame(data)

        # Normalize scores (lower = better)
        for crit in criteria:
            df[crit + "_norm"] = 1 - (df[crit] - df[crit].min()) / (df[crit].max() - df[crit].min() + 1e-9)

        # Weighted Score
        df["Score"] = sum(df[crit + "_norm"] * (weights[crit] / 100) for crit in criteria)
        df = df.sort_values("Score", ascending=False).reset_index(drop=True)

        st.subheader(T.get("results", "Ranking Results"))
        st.dataframe(df[["Name", "Score"] + [c + "_norm" for c in criteria]])

        st.success(f"🏆 {df.iloc[0]['Name']} - {T.get('best_option', 'Best Option')}")

        # Radar chart
        st.subheader(T.get("radar_chart", "Radar Chart"))
        fig = go.Figure()
        for i, row in df.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[row[c + "_norm"] for c in criteria],
                theta=criteria,
                fill='toself',
                name=row["Name"]
            ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True)
        st.plotly_chart(fig)

        # Tornado chart
        st.subheader(T.get("tornado_chart", "Tornado Sensitivity Chart"))
        tornado_df = pd.DataFrame({
            "Criterion": criteria,
            "Impact": [abs(df[crit + "_norm"].max() - df[crit + "_norm"].min()) * (weights[crit] / 100) for crit in criteria]
        }).sort_values("Impact", ascending=True)

        fig2 = go.Figure(go.Bar(
            x=tornado_df["Impact"],
            y=tornado_df["Criterion"],
            orientation='h'
        ))
        fig2.update_layout(title=T.get("tornado_chart", "Tornado Sensitivity Chart"))
        st.plotly_chart(fig2)

        # Export to Excel
        excel_output = io.BytesIO()
        df.to_excel(excel_output, index=False)
        excel_output.seek(0)
        st.download_button(T.get("download_excel", "Download Excel"), excel_output,
                           file_name="equipment_comparison.xlsx", mime="application/vnd.ms-excel")

        # Export to PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=T.get("equipment_comparison_title", "Equipment Comparison Tool"), ln=True)
        for _, row in df.iterrows():
            line = f"{row['Name']}: Score={row['Score']:.2f}"
            pdf.cell(200, 10, txt=line, ln=True)
        pdf_output = io.BytesIO(pdf.output(dest='S').encode('latin-1'))
        st.download_button(T.get("download_pdf", "Download PDF"), pdf_output,
                           file_name="equipment_comparison.pdf", mime="application/pdf")

        # Save/Load from Firebase
        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, "Equipment Comparison", df.to_dict("records"))
            st.success(T.get("save_success", "Saved to Firebase."))

        if st.button(T.get("load", "Load")):
            loaded_data = load_project_data(st.session_state.username, "Equipment Comparison")
            if loaded_data:
                st.write(pd.DataFrame(loaded_data))
                st.success(T.get("load_success", "Loaded from Firebase"))
            else:
                st.warning(T.get("load_warning", "No data found"))

equipment_comparison = run
