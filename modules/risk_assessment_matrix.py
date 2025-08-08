import streamlit as st
import pandas as pd

def run(T):
    st.title("⚠️ Risk Assessment Matrix")

    st.markdown("""
    Evaluate risks using a Likelihood × Consequence matrix.  
    Each risk will be color-coded based on severity.
    """)

    likelihood_scale = {
        "Rare (1)": 1,
        "Unlikely (2)": 2,
        "Possible (3)": 3,
        "Likely (4)": 4,
        "Almost Certain (5)": 5
    }

    consequence_scale = {
        "Insignificant (1)": 1,
        "Minor (2)": 2,
        "Moderate (3)": 3,
        "Major (4)": 4,
        "Catastrophic (5)": 5
    }

    if "risk_log" not in st.session_state:
        st.session_state.risk_log = []

    with st.form("risk_form"):
        description = st.text_input("Describe the Risk")
        likelihood = st.selectbox("Likelihood", list(likelihood_scale.keys()))
        consequence = st.selectbox("Consequence", list(consequence_scale.keys()))
        mitigation = st.text_input("Mitigation / Control Measures")
        submitted = st.form_submit_button("➕ Add Risk")

    if submitted and description:
        score = likelihood_scale[likelihood] * consequence_scale[consequence]
        level = "Low"
        color = "🟩"
        if score >= 15:
            level = "Extreme"
            color = "🟥"
        elif score >= 10:
            level = "High"
            color = "🟧"
        elif score >= 5:
            level = "Medium"
            color = "🟨"

        st.session_state.risk_log.append({
            "Risk": description,
            "Likelihood": likelihood,
            "Consequence": consequence,
            "Score": score,
            "Level": f"{color} {level}",
            "Mitigation": mitigation
        })

    if st.session_state.risk_log:
        st.subheader("📋 Risk Register")
        df = pd.DataFrame(st.session_state.risk_log)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Register", df.to_csv(index=False).encode('utf-8'), "risk_matrix.csv")
