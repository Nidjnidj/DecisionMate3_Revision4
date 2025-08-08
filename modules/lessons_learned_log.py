import streamlit as st
import pandas as pd
from datetime import date

def run(T):
    st.title("📚 Lessons Learned Log")

    st.markdown("""
    Record lessons learned during your project lifecycle.  
    Helps in future risk reduction, quality improvement, and knowledge sharing.
    """)

    if "lessons_log" not in st.session_state:
        st.session_state.lessons_log = []

    with st.form("lesson_form"):
        title = st.text_input("Lesson Title / Summary")
        category = st.selectbox("Category", ["Design", "Procurement", "Construction", "Quality", "Safety", "Other"])
        date_recorded = st.date_input("Date", value=date.today())
        what_happened = st.text_area("📝 What happened?")
        recommendation = st.text_area("✅ Recommendation / Mitigation")

        submitted = st.form_submit_button("➕ Add Lesson")

    if submitted and title:
        st.session_state.lessons_log.append({
            "Title": title,
            "Category": category,
            "Date": str(date_recorded),
            "What Happened": what_happened,
            "Recommendation": recommendation
        })

    if st.session_state.lessons_log:
        st.subheader("📋 Lessons Learned")
        df = pd.DataFrame(st.session_state.lessons_log)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Export Lessons", df.to_csv(index=False).encode('utf-8'), "lessons_learned.csv")
