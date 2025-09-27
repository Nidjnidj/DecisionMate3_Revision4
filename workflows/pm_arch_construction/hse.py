# workflows/pm_arch_construction/hse.py
from __future__ import annotations
import re
from datetime import datetime, date
from typing import Any, Dict, List

import streamlit as st

# artifact registry helpers
from artifact_registry import save_artifact, get_latest

ART_TBX  = "HSE_Toolbox_Log"
ART_INC  = "Incident_Log"
WS_HSE   = "HSE"

# ---------------- utilities ----------------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_rerun():
    rr = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if callable(rr):
        rr()

def _ensure_list(rec: Dict[str, Any] | None, field: str) -> List[Dict[str, Any]]:
    if not rec:
        return []
    data = rec.get("data", {})
    val = data.get(field, [])
    return val if isinstance(val, list) else []

# ---------------- main ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    """HSE module with Toolbox Talks + Incidents logging."""
    st.header("HSE — Toolbox / Incidents")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    # Load latest artifacts (if exist)
    tbx_rec = get_latest(pid, ART_TBX, phid)
    inc_rec = get_latest(pid, ART_INC, phid)

    tbx_rows = _ensure_list(tbx_rec, "rows")
    inc_rows = _ensure_list(inc_rec, "rows")

    tabs = st.tabs(["Toolbox Talks", "Incidents"])

    # ------------------------------------------------------------------ TOOLBOX
    with tabs[0]:
        st.subheader("Toolbox Talks")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            tbx_date = st.date_input("Date", value=date.today(), key=_keyify("tbx_date", pid, phid))
        with c2:
            tbx_crew = st.text_input("Crew / Subcontractor", value="", key=_keyify("tbx_crew", pid, phid))
        with c3:
            tbx_topic = st.text_input("Topic", value="", key=_keyify("tbx_topic", pid, phid))
        with c4:
            tbx_att = st.number_input("Attendees", min_value=0, value=0, step=1, key=_keyify("tbx_att", pid, phid))

        tbx_notes = st.text_area("Key points / notes", value="", key=_keyify("tbx_notes", pid, phid))

        if st.button("➕ Add talk to session", key=_keyify("tbx_add", pid, phid)):
            tbx_rows.append({
                "date": tbx_date.isoformat(),
                "crew": tbx_crew.strip(),
                "topic": tbx_topic.strip(),
                "attendees": int(tbx_att),
                "notes": tbx_notes.strip(),
                "ts": datetime.utcnow().isoformat() + "Z",
            })
            st.success("Talk added (not saved yet).")

        if tbx_rows:
            st.markdown("##### Current talks (unsaved + previously saved)")
            st.dataframe(tbx_rows, use_container_width=True)

        col_s1, col_s2, col_s3 = st.columns(3)
        payload_tbx = {"rows": tbx_rows, "ts": datetime.utcnow().isoformat() + "Z"}
        with col_s1:
            if st.button("💾 Save Toolbox (Draft)", key=_keyify("tbx_save_d", pid, phid)):
                save_artifact(pid, phid, WS_HSE, ART_TBX, payload_tbx, status="Draft")
                st.success("Toolbox log saved (Draft).")
        with col_s2:
            if st.button("💾 Save Toolbox (Pending)", key=_keyify("tbx_save_p", pid, phid)):
                save_artifact(pid, phid, WS_HSE, ART_TBX, payload_tbx, status="Pending")
                st.success("Toolbox log saved (Pending).")
        with col_s3:
            if st.button("✅ Save & Approve Toolbox", key=_keyify("tbx_save_a", pid, phid)):
                rec = save_artifact(pid, phid, WS_HSE, ART_TBX, payload_tbx, status="Pending")
                try:
                    from artifact_registry import approve_artifact
                    approve_artifact(pid, rec.get("artifact_id"))
                except Exception:
                    pass
                st.success("Toolbox log saved and Approved.")
        st.caption(f"Total talks this artifact: **{len(tbx_rows)}**")

    # ------------------------------------------------------------------ INCIDENTS
    with tabs[1]:
        st.subheader("Incidents / Near Misses")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            inc_date = st.date_input("Date", value=date.today(), key=_keyify("inc_date", pid, phid))
        with c2:
            inc_sev = st.selectbox(
                "Severity",
                ["Near Miss", "First Aid", "Recordable", "LTI", "Other"],
                index=0,
                key=_keyify("inc_sev", pid, phid),
            )
        with c3:
            inc_loc = st.text_input("Location", value="", key=_keyify("inc_loc", pid, phid))
        with c4:
            inc_status = st.selectbox("Status", ["Open", "Closed"], index=0, key=_keyify("inc_status", pid, phid))

        desc = st.text_area("Description", value="", key=_keyify("inc_desc", pid, phid))
        cause = st.text_area("Immediate cause / root cause (if known)", value="", key=_keyify("inc_cause", pid, phid))
        corr  = st.text_area("Corrective / preventive actions", value="", key=_keyify("inc_corr", pid, phid))

        if st.button("➕ Add incident to session", key=_keyify("inc_add", pid, phid)):
            inc_rows.append({
                "date": inc_date.isoformat(),
                "severity": inc_sev,
                "location": inc_loc.strip(),
                "status": inc_status,
                "description": desc.strip(),
                "cause": cause.strip(),
                "corrective": corr.strip(),
                "ts": datetime.utcnow().isoformat() + "Z",
            })
            st.success("Incident added (not saved yet).")

        if inc_rows:
            st.markdown("##### Current incidents (unsaved + previously saved)")
            st.dataframe(inc_rows, use_container_width=True)

        col_i1, col_i2, col_i3 = st.columns(3)
        payload_inc = {"rows": inc_rows, "ts": datetime.utcnow().isoformat() + "Z"}
        with col_i1:
            if st.button("💾 Save Incidents (Draft)", key=_keyify("inc_save_d", pid, phid)):
                save_artifact(pid, phid, WS_HSE, ART_INC, payload_inc, status="Draft")
                st.success("Incident log saved (Draft).")
        with col_i2:
            if st.button("💾 Save Incidents (Pending)", key=_keyify("inc_save_p", pid, phid)):
                save_artifact(pid, phid, WS_HSE, ART_INC, payload_inc, status="Pending")
                st.success("Incident log saved (Pending).")
        with col_i3:
            if st.button("✅ Save & Approve Incidents", key=_keyify("inc_save_a", pid, phid)):
                rec = save_artifact(pid, phid, WS_HSE, ART_INC, payload_inc, status="Pending")
                try:
                    from artifact_registry import approve_artifact
                    approve_artifact(pid, rec.get("artifact_id"))
                except Exception:
                    pass
                st.success("Incident log saved and Approved.")
        st.caption(f"Total incidents this artifact: **{len(inc_rows)}**")
