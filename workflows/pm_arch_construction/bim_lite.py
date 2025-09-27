import re
import streamlit as st
from artifact_registry import save_artifact, get_latest

ART = "BIM_Lite"

def _parse_tags(raw: str) -> list[str]:
    parts = re.split(r"[,\n]+", raw or "")
    return [p.strip() for p in parts if p.strip()]

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("BIM-lite Tracker")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    maturity = st.slider("Design maturity (%)", 0, 100, 30)
    sheets_raw = st.text_area("Sheets/models present (comma or newline separated)",
                              "GA plans, Sections, MEP layouts")
    sheets = _parse_tags(sheets_raw)
    issues   = st.text_area("Key design issues", "Coordination, penetrations, clearances …")

    if st.button("Save BIM_Lite (Pending)"):
        save_artifact(pid, phid, "Design", ART,
                      {"maturity_pct": maturity, "register": sheets, "issues": issues},
                      status="Pending")
        st.success("Saved.")
