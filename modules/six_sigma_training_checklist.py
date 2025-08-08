import streamlit as st

def run(T):
    st.title("🎓 Six Sigma Training Checklist")

    st.markdown("""
    Use this checklist to track your progress through Six Sigma certifications:
    - White Belt
    - Yellow Belt
    - Green Belt
    - Black Belt
    """)

    st.subheader("🔖 Select Your Training Level")

    level = st.radio("Select Training Level", ["White Belt", "Yellow Belt", "Green Belt", "Black Belt"])

    training_items = {
        "White Belt": [
            "Introduction to Six Sigma",
            "Understanding Variation",
            "Basic Quality Concepts"
        ],
        "Yellow Belt": [
            "Six Sigma Methodologies",
            "DMAIC Framework",
            "Data Collection Basics",
            "Basic Charts & Graphs"
        ],
        "Green Belt": [
            "Process Mapping",
            "Statistical Process Control",
            "Hypothesis Testing",
            "Project Selection & Scoping"
        ],
        "Black Belt": [
            "Design of Experiments (DOE)",
            "Advanced Statistical Tools",
            "Leadership in Six Sigma Projects",
            "Mentoring Green Belts"
        ]
    }

    with st.form("training_form"):
        st.markdown(f"### 📋 {level} Training Modules")
        completed = []
        for item in training_items[level]:
            if st.checkbox(item):
                completed.append(item)

        submitted = st.form_submit_button("✅ Save Progress")

    if submitted:
        st.success(f"{len(completed)} of {len(training_items[level])} modules completed for {level} level.")
