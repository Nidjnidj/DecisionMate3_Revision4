import re
import streamlit as st
from artifact_registry import save_artifact, get_latest

ART = "AsBuilt_OM"

def _parse_tags(raw: str) -> list[str]:
    parts = re.split(r"[,\n]+", raw or "")
    return [p.strip() for p in parts if p.strip()]

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("As-Built / O&M Binder")
    pid  = project_id or st.session_state.get("current_project_id","P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id","PH-FEL1")

    docs_raw = st.text_area("Documents (names/links — comma or newline separated)",
                            "As-built drawings\nO&M manuals\nTest reports")
    docs = _parse_tags(docs_raw)
    completeness = st.slider("Closeout completeness %", 0, 100, 20)

    if st.button("Save (Pending)"):
        save_artifact(pid, phid, "Handover", ART,
                      {"docs": docs, "complete_pct": completeness},
                      status="Pending")
        st.success("Saved As-Built/O&M status.")
