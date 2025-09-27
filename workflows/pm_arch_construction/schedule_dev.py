import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_WBS  = "WBS"
ART_NET  = "Schedule_Network"

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("Schedule Developer (L2/L3)")
    project_id = project_id or st.session_state.get("current_project_id","P-AC-DEMO")
    phase_id   = phase_id   or st.session_state.get("current_phase_id","PH-FEL1")

    # base template
    template = st.selectbox("Template", ["Building (L2)","Industrial (L2)"], index=0)
    prod = st.number_input("Install productivity (qty/day) – drives durations", 1.0, value=20.0)

    # use BOM if exists to size durations
    bom = get_latest(project_id, "Bill_Of_Materials", phase_id)
    items = (bom or {}).get("data", {}).get("items", [])

    rows = [
        ("Design Complete", 10, []),
        ("Mobilize", 5, ["Design Complete"]),
        ("Substructure", 20, ["Mobilize"]),
        ("Superstructure", 40, ["Substructure"]),
        ("Envelope", 25, ["Superstructure"]),
        ("MEP Rough-In", 35, ["Superstructure"]),
        ("Interior Fit-Out", 45, ["MEP Rough-In","Envelope"]),
        ("Testing & Commissioning", 15, ["Interior Fit-Out"]),
        ("Handover", 5, ["Testing & Commissioning"]),
    ]

    # adjust durations if quantities exist
    if items:
        def qty(item_name):
            for it in items:
                if it["item"].lower().startswith(item_name.lower()):
                    return float(it["qty"])
            return 0.0
        # crude example: envelope duration from brick/block qty
        env_days = max(10, int(qty("Brick/Block")/max(prod,1)))
        rows[4] = ("Envelope", env_days, ["Superstructure"])

    st.table([{"Task":t,"Dur (d)":d,"Pred":",".join(p)} for (t,d,p) in rows])

    if st.button("Save WBS + Network (Pending)"):
        wbs = [{"id":"1","parent":None,"name":"Project","type":"Project"}]
        acts = []
        parent = "1"
        for i,(t,d,p) in enumerate(rows, start=1):
            wbs.append({"id":f"1.{i}","parent":parent,"name":t,"type":"WP"})
            acts.append({"id":f"A{i}","name":t,"wbs_id":f"1.{i}","dur_days":int(d),"predecessors":[f"A{rows.index((x,y,z))+1}" for (x,y,z) in rows if x in p]})
        save_artifact(project_id, phase_id, "Schedule", ART_WBS, {"nodes": wbs}, status="Pending")
        save_artifact(project_id, phase_id, "Schedule", ART_NET, {"activities": acts}, status="Pending")
        st.success("Saved WBS & Network.")
