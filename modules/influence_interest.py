import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from firebase_db import save_project, load_project_data

def run(T):
    title = T.get("influence_interest_title", "Influence & Interest Grid")
    st.header(title)
    st.markdown(T.get("descriptions", {}).get("influence_interest", ""))

    if "grid_entries" not in st.session_state:
        st.session_state.grid_entries = []

    st.subheader(T.get("add_entry", "Add Stakeholder"))
    stakeholder = st.text_input(T.get("stakeholder_name", "Stakeholder Name"))
    influence = st.slider(T.get("influence_level", "Influence Level"), 0, 10, 5)
    interest = st.slider(T.get("interest_level", "Interest Level"), 0, 10, 5)

    if st.button(T.get("add_button", "Add to Grid")) and stakeholder:
        st.session_state.grid_entries.append({
            "Stakeholder": stakeholder,
            "Influence": influence,
            "Interest": interest
        })

    if st.session_state.grid_entries:
        df = pd.DataFrame(st.session_state.grid_entries)
        st.subheader(T.get("grid_table", "Grid Data"))
        st.dataframe(df)

        st.subheader(T.get("visualization", "Influence vs Interest Chart"))
        fig, ax = plt.subplots()
        for _, row in df.iterrows():
            ax.scatter(row["Influence"], row["Interest"], label=row["Stakeholder"])
            ax.text(row["Influence"] + 0.1, row["Interest"] + 0.1, row["Stakeholder"])
        ax.set_xlabel(T.get("influence_level", "Influence Level"))
        ax.set_ylabel(T.get("interest_level", "Interest Level"))
        ax.set_title(title)
        ax.grid(True)
        st.pyplot(fig)

        if st.button(T.get("save", "Save")):
            save_project(st.session_state.username, title, st.session_state.grid_entries)
            st.success(T.get("save_success", "Grid data saved."))

        if st.button(T.get("load", "Load")):
            data = load_project_data(st.session_state.username, title)
            if data:
                st.session_state.grid_entries = data
                st.success(T.get("load_success", "Grid data loaded."))
            else:
                st.warning(T.get("load_warning", "No saved data found."))

influence_interest = run
