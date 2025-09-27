# workflows/pm_arch_construction/qaqc.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_QAQC = "QAQC_Inspections"
ART_NCR  = "NCR_Log"

DISCIPLINES = ["Civil", "Structural", "Architectural", "Mechanical", "Electrical", "Plumbing", "Fire", "IT/ELV", "Process", "Other"]
RESULTS     = ["Pending", "Pass", "Fail", "N/A"]
SEVERITY    = ["Low", "Medium", "High", "Critical"]
NCR_STATUS  = ["Open", "In Progress", "Dispositioned", "Closed"]
DISPOSITION = ["Rework", "Repair", "Use-as-is", "Scrap", "Other"]

# ---------------- helpers ----------------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_date_str(s: str | None) -> str:
    if not s: return ""
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def _listify(raw: str) -> List[str]:
    if not raw: return []
    parts = re.split(r"[,\n;]+", raw)
    return [p.strip() for p in parts if p.strip()]

# ---------------- dataclasses ----------------
@dataclass
class InspRow:
    id: str
    area: str = ""
    discipline: str = "Civil"
    checklist_item: str = ""
    acceptance_criteria: str = ""
    result: str = "Pending"   # Pending/Pass/Fail/N/A
    inspector: str = ""
    date_checked: str = ""    # YYYY-MM-DD
    photos: List[str] = None  # URLs/filenames
    notes: str = ""
    punch_ref: str = ""       # link ref to punchlist (optional)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "area": self.area,
            "discipline": self.discipline,
            "checklist_item": self.checklist_item,
            "acceptance_criteria": self.acceptance_criteria,
            "result": self.result,
            "inspector": self.inspector,
            "date_checked": _safe_date_str(self.date_checked),
            "photos": list(self.photos or []),
            "notes": self.notes,
            "punch_ref": self.punch_ref,
        }

@dataclass
class NCRRow:
    id: str
    related_inspection_id: str = ""
    location: str = ""
    description: str = ""
    severity: str = "Medium"       # Low/Medium/High/Critical
    status: str = "Open"           # Open/In Progress/Dispositioned/Closed
    disposition: str = ""          # Rework/Repair/Use-as-is/...
    corrective_action: str = ""
    root_cause: str = ""
    owner: str = ""
    due_date: str = ""             # YYYY-MM-DD
    date_closed: str = ""          # YYYY-MM-DD
    attachments: List[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "related_inspection_id": self.related_inspection_id,
            "location": self.location,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "disposition": self.disposition,
            "corrective_action": self.corrective_action,
            "root_cause": self.root_cause,
            "owner": self.owner,
            "due_date": _safe_date_str(self.due_date),
            "date_closed": _safe_date_str(self.date_closed),
            "attachments": list(self.attachments or []),
            "notes": self.notes,
        }

# ---------------- CSV IO ----------------
INSP_FIELDS = ["id","area","discipline","checklist_item","acceptance_criteria","result","inspector","date_checked","photos","notes","punch_ref"]
NCR_FIELDS  = ["id","related_inspection_id","location","description","severity","status","disposition","corrective_action","root_cause","owner","due_date","date_closed","attachments","notes"]

def _rows_to_csv(fields: List[str], rows: List[Dict[str, Any]]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for r in rows:
        row = dict(r)
        if "photos" in row and isinstance(row["photos"], list):
            row["photos"] = "; ".join(row["photos"])
        if "attachments" in row and isinstance(row["attachments"], list):
            row["attachments"] = "; ".join(row["attachments"])
        w.writerow({k: row.get(k, "") for k in fields})
    return sio.getvalue().encode("utf-8")

def _csv_to_insp(uploaded) -> List[InspRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[InspRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(InspRow(
                id=(row.get("id") or f"INSP-{i:03d}").strip(),
                area=(row.get("area") or "").strip(),
                discipline=(row.get("discipline") or "Civil").strip(),
                checklist_item=(row.get("checklist_item") or "").strip(),
                acceptance_criteria=(row.get("acceptance_criteria") or "").strip(),
                result=(row.get("result") or "Pending").strip(),
                inspector=(row.get("inspector") or "").strip(),
                date_checked=_safe_date_str(row.get("date_checked")),
                photos=_listify(row.get("photos") or ""),
                notes=(row.get("notes") or "").strip(),
                punch_ref=(row.get("punch_ref") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Inspections): {e}")
        return []

def _csv_to_ncr(uploaded) -> List[NCRRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[NCRRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(NCRRow(
                id=(row.get("id") or f"NCR-{i:03d}").strip(),
                related_inspection_id=(row.get("related_inspection_id") or "").strip(),
                location=(row.get("location") or "").strip(),
                description=(row.get("description") or "").strip(),
                severity=(row.get("severity") or "Medium").strip(),
                status=(row.get("status") or "Open").strip(),
                disposition=(row.get("disposition") or "").strip(),
                corrective_action=(row.get("corrective_action") or "").strip(),
                root_cause=(row.get("root_cause") or "").strip(),
                owner=(row.get("owner") or "").strip(),
                due_date=_safe_date_str(row.get("due_date")),
                date_closed=_safe_date_str(row.get("date_closed")),
                attachments=_listify(row.get("attachments") or ""),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (NCR): {e}")
        return []

# ---------------- metrics ----------------
def _insp_metrics(rows: List[InspRow]) -> Dict[str, Any]:
    total = len(rows)
    passed = sum(1 for r in rows if r.result == "Pass")
    failed = sum(1 for r in rows if r.result == "Fail")
    pending = sum(1 for r in rows if r.result == "Pending")
    pass_rate = round(passed * 100.0 / total, 1) if total else 0.0
    return {"total": total, "passed": passed, "failed": failed, "pending": pending, "pass_rate": pass_rate}

def _ncr_metrics(rows: List[NCRRow]) -> Dict[str, Any]:
    today = date.today().isoformat()
    open_cnt = sum(1 for r in rows if r.status != "Closed")
    closed   = sum(1 for r in rows if r.status == "Closed")
    overdue  = sum(1 for r in rows if r.status != "Closed" and r.due_date and r.due_date < today)
    high     = sum(1 for r in rows if r.status != "Closed" and r.severity in ("High","Critical"))
    return {"open": open_cnt, "closed": closed, "overdue": overdue, "high": high}

# ---------------- seeds ----------------
SEED_INSPECTIONS: List[InspRow] = [
    InspRow(id="INSP-CIV-001", area="Block A - L1", discipline="Civil", checklist_item="Formwork alignment",
            acceptance_criteria="±5mm tolerance; plumb within 3mm/3m", result="Pending"),
    InspRow(id="INSP-STR-002", area="Block A - L1", discipline="Structural", checklist_item="Rebar spacing & cover",
            acceptance_criteria="Spacing per IFC; cover 30mm min", result="Pending"),
    InspRow(id="INSP-MEP-003", area="Core - L2", discipline="Mechanical", checklist_item="Duct support & hangers",
            acceptance_criteria="Spacing per spec; anti-vibration pads installed", result="Pending"),
    InspRow(id="INSP-EL-004", area="Elec. Room L1", discipline="Electrical", checklist_item="Cable termination",
            acceptance_criteria="Lugs crimped; labels installed; torque per spec", result="Pending"),
]

# ---------------- UI tabs ----------------
def _inspections_tab(pid: str, phid: str):
    st.caption("QA/QC inspection checklists and results.")

    latest = get_latest(pid, ART_QAQC, phid)
    rows: List[InspRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [InspRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} inspections")

    state_key = _keyify("qaqc_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows or list(SEED_INSPECTIONS)

    with st.expander("📄 Import / Export / Seed", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Seed common inspections", key=_keyify("qaqc_seed", pid, phid)):
                st.session_state[state_key].extend(SEED_INSPECTIONS)
                st.success(f"Seeded {len(SEED_INSPECTIONS)} rows.")
        with c2:
            up = st.file_uploader("Import Inspections CSV", type=["csv"], key=_keyify("qaqc_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_insp(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} inspections.")
        with c3:
            st.download_button(
                "Download Inspections CSV",
                data=_rows_to_csv(INSP_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_inspections.csv",
                mime="text/csv",
                key=_keyify("qaqc_exp", pid, phid),
            )

    # Filters
    f1, f2, f3 = st.columns([1,1,2])
    with f1:
        f_disc = st.multiselect("Discipline", DISCIPLINES, default=[], key=_keyify("qaqc_fdisc", pid, phid))
    with f2:
        f_res = st.multiselect("Result", RESULTS, default=[], key=_keyify("qaqc_fres", pid, phid))
    with f3:
        f_text = st.text_input("Search", "", key=_keyify("qaqc_ftext", pid, phid))

    def _pass(r: InspRow) -> bool:
        if f_disc and r.discipline not in f_disc: return False
        if f_res and r.result not in f_res: return False
        if f_text:
            blob = " ".join([r.id, r.area, r.discipline, r.checklist_item, r.acceptance_criteria, r.inspector, r.notes, r.punch_ref]).lower()
            if f_text.lower() not in blob: return False
        return True

    # KPIs
    m = _insp_metrics(st.session_state[state_key])
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total", m["total"])
    with k2: st.metric("Pass", m["passed"])
    with k3: st.metric("Fail", m["failed"])
    with k4: st.metric("Pass rate", f"{m['pass_rate']}%")

    st.divider()

    # Add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add inspection", key=_keyify("qaqc_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(InspRow(id=f"INSP-{n:03d}"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("qaqc_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass(r): 
            continue
        with st.expander(f"{r.id} · {r.discipline} · {r.result}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("Row ID", r.id, key=_keyify("qaqc_id", pid, phid, idx))
                r.area = st.text_input("Area/Location", r.area, key=_keyify("qaqc_area", pid, phid, idx))
                r.discipline = st.selectbox("Discipline", DISCIPLINES,
                                            index=max(0, DISCIPLINES.index(r.discipline) if r.discipline in DISCIPLINES else 0),
                                            key=_keyify("qaqc_disc", pid, phid, idx))
            with c2:
                r.checklist_item = st.text_input("Checklist item", r.checklist_item, key=_keyify("qaqc_item", pid, phid, idx))
                r.acceptance_criteria = st.text_area("Acceptance criteria", r.acceptance_criteria, key=_keyify("qaqc_acc", pid, phid, idx))
                r.result = st.selectbox("Result", RESULTS,
                                        index=max(0, RESULTS.index(r.result) if r.result in RESULTS else 0),
                                        key=_keyify("qaqc_res", pid, phid, idx))
            with c3:
                r.inspector = st.text_input("Inspector", r.inspector, key=_keyify("qaqc_insp", pid, phid, idx))
                r.date_checked = st.text_input("Date checked (YYYY-MM-DD)", r.date_checked, key=_keyify("qaqc_date", pid, phid, idx))
                r.punch_ref = st.text_input("Punch ref (optional)", r.punch_ref, key=_keyify("qaqc_punch", pid, phid, idx))

            photos_raw = st.text_area("Photos / links (comma/newline)", ", ".join(r.photos or []), key=_keyify("qaqc_ph", pid, phid, idx))
            r.photos = _listify(photos_raw)
            r.notes = st.text_area("Notes", r.notes, key=_keyify("qaqc_notes", pid, phid, idx))

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save Inspections (Draft)", key=_keyify("qaqc_save_d", pid, phid)):
            save_artifact(pid, phid, "QA/QC", ART_QAQC, payload, status="Draft")
            st.success("QAQC_Inspections saved (Draft).")
    with right:
        if st.button("Save Inspections (Pending)", key=_keyify("qaqc_save_p", pid, phid)):
            save_artifact(pid, phid, "QA/QC", ART_QAQC, payload, status="Pending")
            st.success("QAQC_Inspections saved (Pending).")

def _ncr_tab(pid: str, phid: str):
    st.caption("Nonconformance Reports (NCR) with disposition & CAPA.")

    latest = get_latest(pid, ART_NCR, phid)
    rows: List[NCRRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [NCRRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} NCRs")

    state_key = _keyify("ncr_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import NCR CSV", type=["csv"], key=_keyify("ncr_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_ncr(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} NCRs.")
        with c2:
            st.download_button(
                "Download NCR CSV",
                data=_rows_to_csv(NCR_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_ncr.csv",
                mime="text/csv",
                key=_keyify("ncr_exp", pid, phid),
            )

    # Filters
    f1, f2, f3 = st.columns([1,1,2])
    with f1:
        f_sev = st.multiselect("Severity", SEVERITY, default=[], key=_keyify("ncr_fsev", pid, phid))
    with f2:
        f_stat = st.multiselect("Status", NCR_STATUS, default=[], key=_keyify("ncr_fstat", pid, phid))
    with f3:
        f_text = st.text_input("Search", "", key=_keyify("ncr_ftext", pid, phid))

    def _pass(r: NCRRow) -> bool:
        if f_sev and r.severity not in f_sev: return False
        if f_stat and r.status not in f_stat: return False
        if f_text:
            blob = " ".join([r.id, r.related_inspection_id, r.location, r.description, r.disposition, r.corrective_action, r.owner, r.root_cause, r.notes]).lower()
            if f_text.lower() not in blob: return False
        return True

    # KPIs
    k = _ncr_metrics(st.session_state[state_key])
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Open", k["open"])
    with k2: st.metric("Closed", k["closed"])
    with k3: st.metric("Overdue", k["overdue"])
    with k4: st.metric("High/Critical (Open)", k["high"])

    st.divider()

    # Add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add NCR", key=_keyify("ncr_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(NCRRow(id=f"NCR-{n:03d}"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("ncr_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    today_iso = date.today().isoformat()
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass(r): 
            continue
        with st.expander(f"{r.id} · {r.severity} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("NCR ID", r.id, key=_keyify("ncr_id", pid, phid, idx))
                r.related_inspection_id = st.text_input("Related Inspection ID", r.related_inspection_id, key=_keyify("ncr_insp", pid, phid, idx))
                r.location = st.text_input("Location", r.location, key=_keyify("ncr_loc", pid, phid, idx))
            with c2:
                r.severity = st.selectbox("Severity", SEVERITY,
                                          index=max(0, SEVERITY.index(r.severity) if r.severity in SEVERITY else 1),
                                          key=_keyify("ncr_sev", pid, phid, idx))
                r.status = st.selectbox("Status", NCR_STATUS,
                                        index=max(0, NCR_STATUS.index(r.status) if r.status in NCR_STATUS else 0),
                                        key=_keyify("ncr_stat", pid, phid, idx))
                r.owner = st.text_input("Owner", r.owner, key=_keyify("ncr_owner", pid, phid, idx))
            with c3:
                r.disposition = st.selectbox("Disposition", DISPOSITION,
                                             index=max(0, DISPOSITION.index(r.disposition) if r.disposition in DISPOSITION else 0),
                                             key=_keyify("ncr_disp", pid, phid, idx))
                r.due_date = st.text_input("Due date (YYYY-MM-DD)", r.due_date or today_iso, key=_keyify("ncr_due", pid, phid, idx))
                r.date_closed = st.text_input("Date closed (YYYY-MM-DD)", r.date_closed, key=_keyify("ncr_close", pid, phid, idx))

            r.corrective_action = st.text_area("Corrective Action (CAPA)", r.corrective_action, key=_keyify("ncr_capa", pid, phid, idx))
            r.root_cause = st.text_area("Root Cause", r.root_cause, key=_keyify("ncr_rca", pid, phid, idx))
            attach_raw = st.text_area("Attachments (links/names, comma/newline)", ", ".join(r.attachments or []), key=_keyify("ncr_att", pid, phid, idx))
            r.attachments = _listify(attach_raw)
            r.notes = st.text_area("Notes", r.notes, key=_keyify("ncr_notes", pid, phid, idx))

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save NCRs (Draft)", key=_keyify("ncr_save_d", pid, phid)):
            save_artifact(pid, phid, "QA/QC", ART_NCR, payload, status="Draft")
            st.success("NCR_Log saved (Draft).")
    with right:
        if st.button("Save NCRs (Pending)", key=_keyify("ncr_save_p", pid, phid)):
            save_artifact(pid, phid, "QA/QC", ART_NCR, payload, status="Pending")
            st.success("NCR_Log saved (Pending).")

# ---------------- main entry ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("QA/QC Inspections & NCRs")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    t1, t2 = st.tabs(["Inspections", "NCRs"])
    with t1:
        _inspections_tab(pid, phid)
    with t2:
        _ncr_tab(pid, phid)
