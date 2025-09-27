# workflows/pm_arch_construction/design_reviews.py
from __future__ import annotations
import csv
import io
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import re

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE = "Design_Issue_Log"

DISCIPLINES = ["Architecture", "Structure", "MEP", "Civil", "Landscape", "Fire", "IT/ELV", "Other"]
SEVERITIES  = ["Low", "Medium", "High", "Critical"]
STATUSES    = ["Open", "In Review", "Closed", "Deferred"]

# ---------- helpers ----------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_date_str(s: str | None) -> str:
    if not s:
        return ""
    try:
        # accept YYYY-MM-DD or DD/MM/YYYY etc; normalize to YYYY-MM-DD
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(s.strip(), fmt).date().isoformat()
            except Exception:
                pass
        # last resort, return as-is
        return s.strip()
    except Exception:
        return ""

@dataclass
class IssueRow:
    id: str
    discipline: str = "Architecture"
    location: str = ""
    description: str = ""
    severity: str = "Medium"
    status: str = "Open"
    assignee: str = ""
    due: str = ""              # YYYY-MM-DD
    ref: str = ""              # drawing/spec ref
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["due"] = _safe_date_str(self.due)
        return d

# quick seeds per discipline
SEEDS: Dict[str, List[IssueRow]] = {
    "Architecture": [
        IssueRow(id="ARC-001", discipline="Architecture", description="Door clear width below code minimum", severity="High", status="Open", ref="A-DR-101"),
        IssueRow(id="ARC-002", discipline="Architecture", description="Corridor width non-compliant at level 2", severity="Critical", status="Open", ref="A-PL-202"),
    ],
    "Structure": [
        IssueRow(id="STR-001", discipline="Structure", description="Beam clash with duct at grid C/5", severity="High", status="Open", ref="S-FR-310"),
    ],
    "MEP": [
        IssueRow(id="MEP-001", discipline="MEP", description="Insufficient ceiling void for FCU maintenance", severity="Medium", status="Open", ref="M-HVAC-401"),
    ],
    "Civil": [
        IssueRow(id="CIV-001", discipline="Civil", description="Storm line invert too shallow near south gate", severity="Medium", status="Open", ref="C-UG-112"),
    ],
}

# ---------- csv io ----------
CSV_FIELDS = ["id", "discipline", "location", "description", "severity", "status", "assignee", "due", "ref", "notes"]

def _rows_to_csv(rows: List[IssueRow]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=CSV_FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow(r.to_dict())
    return sio.getvalue().encode("utf-8")

def _csv_to_rows(uploaded) -> List[IssueRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[IssueRow] = []
        for row in rd:
            out.append(IssueRow(
                id=(row.get("id") or "").strip() or f"ISS-{len(out)+1:03d}",
                discipline=(row.get("discipline") or "Architecture").strip(),
                location=(row.get("location") or "").strip(),
                description=(row.get("description") or "").strip(),
                severity=(row.get("severity") or "Medium").strip(),
                status=(row.get("status") or "Open").strip(),
                assignee=(row.get("assignee") or "").strip(),
                due=_safe_date_str(row.get("due")),
                ref=(row.get("ref") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return []

# ---------- core ui ----------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Design Review Matrix / Issue Log")
    pid = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    # load latest
    latest = get_latest(pid, ART_TYPE, phid)
    if latest:
        data = latest.get("data", {}) or {}
        rows = [IssueRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} issues")
    else:
        rows = []

    # keep in session during edit
    state_key = _keyify("dr_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    # top bar: seeding / import / export
    with st.expander("📄 Import / Export / Seeding", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            seed_d = st.selectbox("Seed discipline template", list(SEEDS.keys()), index=0, key=_keyify("dr_seed_sel", pid, phid))
            if st.button("Seed rows", key=_keyify("dr_seed_btn", pid, phid, seed_d)):
                st.session_state[state_key].extend(SEEDS[seed_d])
                st.success(f"Seeded {len(SEEDS[seed_d])} issue(s).")
        with c2:
            up = st.file_uploader("Import CSV", type=["csv"], key=_keyify("dr_import", pid, phid))
            if up is not None:
                parsed = _csv_to_rows(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} issues.")
        with c3:
            st.download_button(
                "Download CSV",
                data=_rows_to_csv(st.session_state[state_key]),
                file_name=f"{pid}_{phid}_design_issue_log.csv",
                mime="text/csv",
                key=_keyify("dr_export", pid, phid),
            )

    st.divider()

    # filters
    f1, f2, f3, f4 = st.columns([1,1,1,2])
    with f1:
        filt_disc = st.multiselect("Discipline", options=DISCIPLINES, default=[], key=_keyify("dr_f_disc", pid, phid))
    with f2:
        filt_sev = st.multiselect("Severity", options=SEVERITIES, default=[], key=_keyify("dr_f_sev", pid, phid))
    with f3:
        filt_stat = st.multiselect("Status", options=STATUSES, default=[], key=_keyify("dr_f_stat", pid, phid))
    with f4:
        search = st.text_input("Search text", "", key=_keyify("dr_f_txt", pid, phid))

    def _pass_filters(r: IssueRow) -> bool:
        if filt_disc and r.discipline not in filt_disc: return False
        if filt_sev and r.severity not in filt_sev: return False
        if filt_stat and r.status not in filt_stat: return False
        if search:
            s = search.lower()
            blob = " ".join([r.id, r.discipline, r.location, r.description, r.assignee, r.ref, r.notes]).lower()
            if s not in blob: return False
        return True

    # stats
    def _stats(rows: List[IssueRow]) -> Dict[str, Any]:
        tot = len(rows)
        open_cnt = sum(1 for r in rows if r.status != "Closed")
        critical = sum(1 for r in rows if r.severity == "Critical" and r.status != "Closed")
        high     = sum(1 for r in rows if r.severity == "High" and r.status != "Closed")
        return {"total": tot, "open": open_cnt, "critical": critical, "high": high}

    stats_all  = _stats(st.session_state[state_key])
    stats_view = _stats([r for r in st.session_state[state_key] if _pass_filters(r)])

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Total", stats_all["total"])
    with k2: st.metric("Open (all)", stats_all["open"])
    with k3: st.metric("Critical (all)", stats_all["critical"])
    with k4: st.metric("Open (filtered)", stats_view["open"])
    with k5: st.metric("Critical (filtered)", stats_view["critical"])

    st.caption("Tip: Use filters to focus the editor view. Saving persists *all* rows, not just filtered ones.")

    st.divider()

    # add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add row", key=_keyify("dr_add", pid, phid)):
            next_num = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(IssueRow(id=f"ISS-{next_num:03d}"))
    with crem:
        if st.button("🗑️ Remove last (filtered view unaffected)", key=_keyify("dr_remove", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # editor (one expander per row that passes the filters)
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass_filters(r):
            continue
        with st.expander(f"{r.id} · {r.discipline} · {r.severity} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("ID", value=r.id, key=_keyify("dr_id", pid, phid, idx))
                r.discipline = st.selectbox("Discipline", DISCIPLINES, index=max(0, DISCIPLINES.index(r.discipline) if r.discipline in DISCIPLINES else 0),
                                            key=_keyify("dr_disc", pid, phid, idx))
                r.severity = st.selectbox("Severity", SEVERITIES, index=max(0, SEVERITIES.index(r.severity) if r.severity in SEVERITIES else 1),
                                          key=_keyify("dr_sev", pid, phid, idx))
            with c2:
                r.status = st.selectbox("Status", STATUSES, index=max(0, STATUSES.index(r.status) if r.status in STATUSES else 0),
                                        key=_keyify("dr_stat", pid, phid, idx))
                r.assignee = st.text_input("Assignee", value=r.assignee, key=_keyify("dr_asg", pid, phid, idx))
                r.due = st.text_input("Due (YYYY-MM-DD)", value=r.due, key=_keyify("dr_due", pid, phid, idx))
            with c3:
                r.location = st.text_input("Location/Room/Grid", value=r.location, key=_keyify("dr_loc", pid, phid, idx))
                r.ref = st.text_input("Ref (drawing/spec)", value=r.ref, key=_keyify("dr_ref", pid, phid, idx))
            r.description = st.text_area("Description", value=r.description, key=_keyify("dr_desc", pid, phid, idx))
            r.notes = st.text_area("Notes", value=r.notes, key=_keyify("dr_notes", pid, phid, idx))

    st.divider()

    # save
    left, right = st.columns(2)
    payload = {
        "rows": [r.to_dict() for r in st.session_state[state_key]],
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    with left:
        if st.button("Save as Draft", key=_keyify("dr_save_draft", pid, phid)):
            save_artifact(pid, phid, "Design", ART_TYPE, payload, status="Draft")
            st.success("Design_Issue_Log saved (Draft).")
    with right:
        if st.button("Save as Pending", key=_keyify("dr_save_pending", pid, phid)):
            save_artifact(pid, phid, "Design", ART_TYPE, payload, status="Pending")
            st.success("Design_Issue_Log saved (Pending).")
