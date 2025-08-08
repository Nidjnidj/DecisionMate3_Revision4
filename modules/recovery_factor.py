import streamlit as st

def run(T):
    st.header("📊 Recovery Factor Estimator")

    st.markdown("### Step 1: Input Original Hydrocarbons In Place")

    fluid_type = st.selectbox("Fluid Type", ["Oil", "Gas"])
    N = st.number_input(f"Original {'Oil' if fluid_type == 'Oil' else 'Gas'} in Place (STB or SCF)", min_value=0.0)

    st.markdown("### Step 2: Select Drive Mechanism")
    
    if fluid_type == "Oil":
        mechanisms = {
            "Solution Gas Drive": (0.05, 0.30),
            "Gas Cap Expansion": (0.15, 0.35),
            "Water Drive": (0.35, 0.60),
            "Gravity Drainage": (0.20, 0.50),
            "Combination Drive": (0.25, 0.55),
        }
    else:
        mechanisms = {
            "Dry Gas Reservoir": (0.70, 0.90),
            "Condensate Reservoir": (0.30, 0.70),
        }

    selected = st.selectbox("Drive Mechanism", list(mechanisms.keys()))
    min_rf, max_rf = mechanisms[selected]

    st.markdown(f"**Typical Recovery Factor Range**: {min_rf*100:.1f}% – {max_rf*100:.1f}%")

    custom_rf = st.slider("Adjust Recovery Factor (%)", int(min_rf*100), int(max_rf*100), int((min_rf+max_rf)*50))
    rf = custom_rf / 100

    if st.button("Estimate Recoverable Reserves"):
        recoverable = N * rf
        unit = "barrels" if fluid_type == "Oil" else "scf"
        st.success(f"Estimated Recoverable Reserves: {recoverable:,.2f} {unit}")
