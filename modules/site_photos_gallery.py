import streamlit as st
from datetime import datetime
from firebase_db import save_project, load_project_data

FIREBASE_KEY = "site_photos_gallery"

def site_photos_gallery(T):
    st.subheader("📸 Site Photos Gallery")

    if "site_photos" not in st.session_state:
        data_dict = load_project_data(st.session_state.username, FIREBASE_KEY)
        st.session_state.site_photos = data_dict["data"] if data_dict and "data" in data_dict else []

    with st.form("upload_photo_form"):
        photo_file = st.file_uploader("📤 Upload Site Photo", type=["jpg", "jpeg", "png"])
        caption = st.text_input("📌 Caption")
        date = st.date_input("📅 Date", value=datetime.today())

        submit = st.form_submit_button("➕ Add to Gallery")
        if submit and photo_file is not None:
            photo_bytes = photo_file.read()
            st.session_state.site_photos.append({
                "Date": str(date),
                "Caption": caption,
                "Image": photo_bytes
            })
            st.success("✅ Photo added to gallery!")

    if st.session_state.site_photos:
        st.markdown("### 🖼️ Gallery")
        for i, photo in enumerate(st.session_state.site_photos):
            st.image(photo["Image"], caption=f'{photo["Date"]} - {photo["Caption"]}', use_column_width=True)
            st.markdown("---")

        if st.button("💾 Save Gallery"):
            # Note: Binary data cannot be saved in Firestore. Only metadata saved.
            save_project(st.session_state.username, FIREBASE_KEY, [
                {k: v for k, v in p.items() if k != "Image"} for p in st.session_state.site_photos
            ])
            st.warning("⚠️ Only metadata (caption & date) saved due to image limitations.")
