import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def run(T):
    st.header(T.get("layout_planner_title", "House Layout Planner"))
    st.markdown(T.get("descriptions", {}).get("house_layout_planner", "Define your house layout using grid-based planning."))

    rows = st.number_input(T.get("num_rows", "Grid Rows"), min_value=3, max_value=20, value=10)
    cols = st.number_input(T.get("num_cols", "Grid Columns"), min_value=3, max_value=20, value=10)

    room_types = ["Bedroom", "Living Room", "Kitchen", "Bathroom", "Hall", "Balcony", "Storage"]
    room = st.selectbox(T.get("select_room", "Select Room Type"), room_types)
    color = st.color_picker(T.get("room_color", "Room Color"), "#ADD8E6")

    if "layout" not in st.session_state:
        st.session_state.layout = np.full((int(rows), int(cols)), "")
        st.session_state.colors = np.full((int(rows), int(cols)), "")

    st.write(T.get("click_grid", "Click on grid cells to assign selected room type."))

    grid = st.empty()
    edited = False
    for i in range(int(rows)):
        cols_list = []
        for j in range(int(cols)):
            label = st.session_state.layout[i, j] or "⬜"
            btn = st.button(label, key=f"cell_{i}_{j}")
            if btn:
                st.session_state.layout[i, j] = room
                st.session_state.colors[i, j] = color
                edited = True
        st.write(" ")

    if st.button(T.get("reset_layout", "Reset Layout")):
        st.session_state.layout = np.full((int(rows), int(cols)), "")
        st.session_state.colors = np.full((int(rows), int(cols)), "")

    if st.button(T.get("show_plan", "Show Plan Preview")):
        fig = go.Figure()
        for i in range(int(rows)):
            for j in range(int(cols)):
                label = st.session_state.layout[i, j]
                bg_color = st.session_state.colors[i, j] or "white"
                fig.add_shape(type="rect",
                              x0=j, x1=j+1,
                              y0=rows-i-1, y1=rows-i,
                              line=dict(color="black"), fillcolor=bg_color)
                fig.add_annotation(x=j+0.5, y=rows-i-0.5, text=label,
                                   showarrow=False, font=dict(size=8))
        fig.update_layout(width=500, height=500, margin=dict(l=10, r=10, t=10, b=10),
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        st.plotly_chart(fig, use_container_width=True)

house_layout_planner = run
