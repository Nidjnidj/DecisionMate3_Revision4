import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE = "Site_Screener"

def run(project_id: str|None=None, phase_id: str|None=None):
    st.subheader("Site Screener")
    project_id = project_id or st.session_state.get("current_project_id","P-AC-DEMO")
    phase_id   = phase_id   or st.session_state.get("current_phase_id","PH-FEL1")

    crits = ["Zoning", "Utilities", "Access", "Flood", "Topography", "Cost"]
    weights = {}
    st.caption("Weight your criteria (0–10).")
    cols = st.columns(len(crits))
    for i,c in enumerate(crits):
        with cols[i]:
            weights[c] = st.number_input(c, 0.0, 10.0, 5.0, key=f"w_{c}")

    st.divider()
    st.caption("Score candidate sites (0–10).")
    num = st.number_input("How many sites?", 1, 10, 3)
    sites = []
    for i in range(num):
        with st.expander(f"Site {i+1}"):
            name = st.text_input("Name", f"Site-{i+1}", key=f"n{i}")
            row = {}
            row["name"] = name
            for c in crits:
                row[c] = st.number_input(f"{c} score", 0.0, 10.0, 5.0, key=f"s_{c}_{i}")
            sites.append(row)

    # simple weighted score
    totals = []
    for r in sites:
        score = sum(r[c]*weights[c] for c in crits) / max(1,sum(weights.values()))
        totals.append((r["name"], round(score,2)))
    if totals:
        best = sorted(totals, key=lambda x: x[1], reverse=True)[0]
        st.metric("Top site", f"{best[0]} ({best[1]})")

    if st.button("Save Screener (Pending)"):
        payload = {"criteria": weights, "sites": sites, "scores": totals}
        save_artifact(project_id, phase_id, "Site", ART_TYPE, payload, status="Pending")
        st.success("Site_Screener saved.")
