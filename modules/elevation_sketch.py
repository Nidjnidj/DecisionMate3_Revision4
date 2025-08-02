import streamlit as st
import plotly.graph_objects as go

def run(T):
    st.header(T.get("elevation_sketch_title", "Elevation Sketch Tool"))
    st.markdown(T.get("descriptions", {}).get("elevation_sketch", "Sketch basic front or side elevation of your house."))

    elements = []

    with st.form("elevation_form"):
        st.subheader(T.get("add_element", "Add Elevation Element"))
        label = st.text_input(T.get("label", "Label"), value="Wall")
        x_start = st.number_input("X Start (m)", min_value=0.0, step=0.5, value=0.0)
        x_end = st.number_input("X End (m)", min_value=0.0, step=0.5, value=3.0)
        y_start = st.number_input("Y Base (m)", min_value=0.0, step=0.5, value=0.0)
        height = st.number_input("Height (m)", min_value=0.0, step=0.5, value=3.0)
        color = st.color_picker(T.get("element_color", "Element Color"), "#D3D3D3")

        submitted = st.form_submit_button(T.get("add_to_sketch", "Add to Sketch"))
        if submitted:
            elements.append({
                "label": label,
                "x0": x_start,
                "x1": x_end,
                "y0": y_start,
                "y1": y_start + height,
                "color": color
            })

    if st.button(T.get("draw_elevation", "Draw Elevation")):
        fig = go.Figure()
        for el in elements:
            fig.add_shape(type="rect",
                          x0=el["x0"], x1=el["x1"],
                          y0=el["y0"], y1=el["y1"],
                          line=dict(color="black"),
                          fillcolor=el["color"])
            fig.add_annotation(x=(el["x0"] + el["x1"]) / 2,
                               y=(el["y0"] + el["y1"]) / 2,
                               text=el["label"],
                               showarrow=False)

        fig.update_layout(height=500, width=800, xaxis_title="Width (m)", yaxis_title="Height (m)",
                          xaxis=dict(scaleanchor="y", scaleratio=1), yaxis=dict(range=[0, 5]))
        st.plotly_chart(fig)


        st.success(T.get("sketch_ready", "Elevation sketch generated."))

elevation_sketch = run
