import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_PACKS = "Procurement_Packages"
ART_LLI   = "Long_Lead_Items"

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("Procurement Packages & Long-Lead")
    project_id = project_id or st.session_state.get("current_project_id","P-AC-DEMO")
    phase_id   = phase_id   or st.session_state.get("current_phase_id","PH-FEL1")

    num = st.number_input("Packages", 1, 20, 4)
    packs = []
    for i in range(num):
        with st.expander(f"Package {i+1}"):
            name = st.text_input("Name", f"PKG-{i+1}", key=f"p{i}")
            scope= st.text_area("Scope", "Supply & install …", key=f"s{i}")
            date = st.date_input("ITB issue", key=f"d{i}")
            packs.append({"name":name,"scope":scope,"itb_date":str(date)})

    st.divider()
    st.caption("Long-lead items")
    m = st.number_input("LLI count", 0, 50, 3)
    lli = []
    for j in range(m):
        with st.expander(f"LLI {j+1}"):
            item = st.text_input("Item", f"Transformer-{j+1}", key=f"ll{j}")
            lead = st.number_input("Lead time (days)", 1, 1000, 180, key=f"ld{j}")
            need = st.date_input("Needed on site", key=f"nd{j}")
            lli.append({"item":item,"lead_days":int(lead),"need_by":str(need)})

    if st.button("Save Procurement (Pending)"):
        save_artifact(project_id, phase_id, "Procurement", ART_PACKS, {"packages":packs}, status="Pending")
        save_artifact(project_id, phase_id, "Procurement", ART_LLI,   {"lli":lli}, status="Pending")
        st.success("Saved packages & LLI.")
