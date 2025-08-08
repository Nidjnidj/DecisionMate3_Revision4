import streamlit as st

def run(T):
    st.title("🚑 Emergency Response Plan Generator")

    st.markdown("""
    Create a basic ERP by defining key roles, hazards, assembly points, and emergency contacts.
    """)

    st.subheader("📍 Site & Hazard Info")
    site_name = st.text_input("Site / Project Name")
    main_hazards = st.text_area("List Major Hazards (fire, gas release, chemicals, etc.)")
    assembly_point = st.text_input("Assembly Point Location")

    st.subheader("👷 Emergency Roles")
    er_lead = st.text_input("Emergency Response Team Lead")
    fire_warden = st.text_input("Fire Warden")
    first_aider = st.text_input("First Aid Responder")

    st.subheader("📞 Emergency Contact Info")
    fire_contact = st.text_input("Fire Department Contact")
    medical_contact = st.text_input("Medical / Ambulance")
    security_contact = st.text_input("Site Security")

    if st.button("🧾 Generate ERP Summary"):
        st.markdown("---")
        st.subheader("📋 ERP Summary")
        st.markdown(f"**Site Name:** {site_name}")
        st.markdown(f"**Main Hazards:** {main_hazards}")
        st.markdown(f"**Assembly Point:** {assembly_point}")

        st.markdown("### 👨‍🚒 Key Roles")
        st.markdown(f"- Emergency Team Lead: {er_lead}")
        st.markdown(f"- Fire Warden: {fire_warden}")
        st.markdown(f"- First Aider: {first_aider}")

        st.markdown("### ☎️ Emergency Contacts")
        st.markdown(f"- Fire: {fire_contact}")
        st.markdown(f"- Medical: {medical_contact}")
        st.markdown(f"- Security: {security_contact}")
