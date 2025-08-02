import streamlit as st

def room_sizing_estimator(T):
    st.header("🏠 " + T.get("room_sizing_estimator_title", "Room Sizing Estimator"))

    room_length = st.number_input("Room Length (m)", min_value=1.0, value=4.0)
    room_width = st.number_input("Room Width (m)", min_value=1.0, value=3.0)
    room_height = st.number_input("Room Height (m)", min_value=2.0, value=2.5)

    if st.button("Calculate Area and Volume"):
        area = room_length * room_width
        volume = area * room_height
        st.success(f"📐 Floor Area: {area:.2f} m²")
        st.success(f"📦 Room Volume: {volume:.2f} m³")

    st.markdown("---")
    st.caption("This tool helps you estimate room area and volume for basic planning and ventilation sizing.")
