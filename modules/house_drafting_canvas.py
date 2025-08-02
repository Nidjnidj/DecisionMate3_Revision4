import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

def run(T):
    st.header(T.get("drafting_canvas_title", "House Drafting Canvas"))
    st.markdown(T.get("descriptions", {}).get("house_drafting_canvas", "Sketch simple walls, windows, and doors on a canvas."))

    stroke_width = st.slider(T.get("stroke_width", "Line Thickness"), 1, 5, 2)
    stroke_color = st.color_picker(T.get("stroke_color", "Stroke Color"), "#000000")
    bg_color = st.color_picker(T.get("bg_color", "Canvas Background Color"), "#ffffff")
    drawing_mode = st.selectbox(T.get("drawing_mode", "Drawing Tool"), ["freedraw", "line", "rect", "circle", "transform"])
    update_button = st.button(T.get("update_canvas", "Update Canvas"))

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color=bg_color,
        update_streamlit=update_button,
        height=500,
        width=700,
        drawing_mode=drawing_mode,
        key="canvas1",
    )

    if canvas_result.image_data is not None:
        st.image(canvas_result.image_data)

    if canvas_result.json_data is not None:
        st.download_button(T.get("download_drawing", "Download Drawing Data"),
                           data=str(canvas_result.json_data),
                           file_name="house_drawing.json")

house_drafting_canvas = run
