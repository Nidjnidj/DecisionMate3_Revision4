import streamlit as st

def run(T):
    st.title("🔍 Root Cause Analysis Tool")

    st.markdown("""
    This module supports two classic RCA techniques:
    - **5 Whys**: Explore the underlying cause by repeatedly asking "Why?"
    - **Fishbone Diagram (Ishikawa)**: Categorize possible root causes into logical buckets.
    """)

    st.subheader("🧠 5 Whys")

    problem = st.text_input("❗ Define the Problem")
    whys = []

    for i in range(1, 6):
        why = st.text_input(f"Why {i}?", key=f"why_{i}")
        whys.append(why)

    if st.button("📘 Show 5 Whys Summary"):
        if problem.strip() == "" or any(w.strip() == "" for w in whys):
            st.error("Please complete all 5 Whys.")
        else:
            st.markdown("### 🔄 Chain of Causes:")
            st.markdown(f"**Problem:** {problem}")
            for i, w in enumerate(whys, 1):
                st.markdown(f"**Why {i}?** {w}")

    st.markdown("---")
    st.subheader("🐟 Fishbone (Ishikawa) Categories")

    categories = ["People", "Process", "Equipment", "Materials", "Environment", "Management"]
    fishbone_data = {}

    for cat in categories:
        cause = st.text_area(f"✏️ Possible causes under {cat}:", key=f"fishbone_{cat}")
        fishbone_data[cat] = cause

    if st.button("📊 Show Fishbone Summary"):
        st.markdown("### 🐟 Root Cause Categories Summary")
        for cat, txt in fishbone_data.items():
            st.markdown(f"**{cat}:** {txt if txt else '_No input_'}")
