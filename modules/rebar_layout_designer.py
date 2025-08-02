import streamlit as st

def rebar_layout_designer(T):
    st.header("🧱 " + T.get("rebar_layout_designer_title", "Rebar Layout Designer"))

    st.markdown("### Input Parameters for Slab Rebar Layout")

    slab_length = st.number_input("Slab Length (m)", min_value=1.0, value=5.0)
    slab_width = st.number_input("Slab Width (m)", min_value=1.0, value=3.0)
    bar_spacing = st.number_input("Bar Spacing (mm)", min_value=50, value=200)
    bar_diameter = st.selectbox("Bar Diameter (mm)", [8, 10, 12, 16, 20])

    if st.button("Generate Rebar Layout"):
        num_bars_length = int((slab_length * 1000) / bar_spacing) + 1
        num_bars_width = int((slab_width * 1000) / bar_spacing) + 1
        total_bars = num_bars_length + num_bars_width

        st.success("✅ Estimated Rebar Requirements:")
        st.write(f"**Bars along length:** {num_bars_length}")
        st.write(f"**Bars along width:** {num_bars_width}")
        st.write(f"**Total bars required:** {total_bars}")
        st.write(f"**Bar Diameter:** {bar_diameter} mm")

    st.caption("Note: This tool gives a simple estimation. Always validate with structural standards.")
