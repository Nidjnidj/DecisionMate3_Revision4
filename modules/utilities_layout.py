import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def run(T):
    st.header(T.get("utilities_layout_title", "Utilities Layout Planner"))
    st.markdown(T.get("descriptions", {}).get("utilities_layout", "Mark electrical and plumbing points on a layout."))

    rows = st.number_input(T.get("layout_rows", "Grid Rows"), min_value=3, max_value=20, value=10)
    cols = st.number_input(T.get("layout_cols", "Grid Columns"), min_value=3, max_value=20, value=10)

    util_types = ["Socket", "Switch", "Light", "Water Tap", "Drain Point"]
    selected_util = st.selectbox(T.get("select_util", "Select Utility Type"), util_types)
    color = st.color_picker(T.get("util_color", "Utility Marker Color"), "#FF5733")

    if "util_map" not in st.session_state:
        st.session_state.util_map = {}

    st.write(T.get("click_to_place", "Click cell coordinates to place utility."))

    for i in range(int(rows)):
        cols_row = st.columns(int(cols))
        for j in range(int(cols)):
            label = f"{i},{j}"
            if cols_row[j].button(label, key=f"util_{i}_{j}"):
                st.session_state.util_map[f"{i},{j}"] = {"type": selected_util, "color": color}

    if st.button(T.get("clear_util", "Clear Utilities")):
        st.session_state.util_map = {}

    if st.button(T.get("preview_util", "Show Layout Preview")):
        fig = go.Figure()
        for i in range(int(rows)):
            for j in range(int(cols)):
                label = ""
                color_box = "#f2f2f2"
                if f"{i},{j}" in st.session_state.util_map:
                    label = st.session_state.util_map[f"{i},{j}"]["type"]
                    color_box = st.session_state.util_map[f"{i},{j}"]["color"]
                fig.add_shape(type="rect", x0=j, x1=j+1, y0=rows-i-1, y1=rows-i,
                              line=dict(color="black"), fillcolor=color_box)
                fig.add_annotation(x=j+0.5, y=rows-i-0.5, text=label,
                                   showarrow=False, font=dict(size=8))

        fig.update_layout(width=500, height=500, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True)

utilities_layout = run
