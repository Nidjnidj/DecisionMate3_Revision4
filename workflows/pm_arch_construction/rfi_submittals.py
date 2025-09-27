# workflows/pm_arch_construction/rfi_submittals.py
from __future__ import annotations
import csv
import io
import re
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_RFI  = "RFI_Log"
ART_SUB  = "Submittal_Log"

DISCIPLINES = ["Architecture", "Structure", "MEP", "Civil", "Landscape", "Fire", "IT/ELV", "Other"]
RFI_STATUSES = ["Open", "Answered", "Closed", "Void"]
RFI_PRIORITIES = ["Normal", "High", "Urgent"]

SUB_STATUSES = ["Submitted", "Revise & Resubmit", "Approved as Noted", "Approved", "Rejected", "Closed"]

# ---------------- utilities ----------------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_date_str(s: str | None) -> str:
    if not s:
        return ""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    # last resort: return as-is
    return s

def _parse_date(s: str | None) -> Optional[date]:
    s = _safe_date_str(s)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _listify(raw: str) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,\n]+", raw)
    return [p.strip() for p in parts if p.strip()]

# ---------------- dataclasses ----------------
@dataclass
class RFIItem:
    id: str
    subject: str = ""
    discipline: str = "Architecture"
    spec_ref: str = ""
    drawing_ref: str = ""
    question: str = ""
    status: str = "Open"
    priority: str = "Normal"
    asked_by: str = ""
    asked_to: str = ""
    date_sent: str = ""      # YYYY-MM-DD
    date_due: str = ""       # YYYY-MM-DD
    date_answered: str = ""  # YYYY-MM-DD
    response_summary: str = ""
    wbs_id: str = ""
    activity_id: str = ""
    link: str = ""
    attachments: List[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "discipline": self.discipline,
            "spec_ref": self.spec_ref,
            "drawing_ref": self.drawing_ref,
            "question": self.question,
            "status": self.status,
            "priority": self.priority,
            "asked_by": self.asked_by,
            "asked_to": self.asked_to,
            "date_sent": _safe_date_str(self.date_sent),
            "date_due": _safe_date_str(self.date_due),
            "date_answered": _safe_date_str(self.date_answered),
            "response_summary": self.response_summary,
            "wbs_id": self.wbs_id,
            "activity_id": self.activity_id,
            "link": self.link,
            "attachments": list(self.attachments or []),
            "notes": self.notes,
        }

@dataclass
class SubmittalItem:
    id: str
    package: str = ""
    spec_section: str = ""
    title: str = ""
    discipline: str = "Architecture"
    status: str = "Submitted"
    submitted_by: str = ""
    reviewer: str = ""
    date_submitted: str = ""   # YYYY-MM-DD
    date_required: str = ""    # YYYY-MM-DD
    date_returned: str = ""    # YYYY-MM-DD
    wbs_id: str = ""
    activity_id: str = ""
    link: str = ""
    attachments: List[str] = None
    comments: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "package": self.package,
            "spec_section": self.spec_section,
            "title": self.title,
            "discipline": self.discipline,
            "status": self.status,
            "submitted_by": self.submitted_by,
            "reviewer": self.reviewer,
            "date_submitted": _safe_date_str(self.date_submitted),
            "date_required": _safe_date_str(self.date_required),
            "date_returned": _safe_date_str(self.date_returned),
            "wbs_id": self.wbs_id,
            "activity_id": self.activity_id,
            "link": self.link,
            "attachments": list(self.attachments or []),
            "comments": self.comments,
        }

# ---------------- CSV IO ----------------
RFI_FIELDS = ["id","subject","discipline","spec_ref","drawing_ref","question","status","priority","asked_by","asked_to","date_sent","date_due","date_answered","response_summary","wbs_id","activity_id","link","attachments","notes"]
SUB_FIELDS = ["id","package","spec_section","title","discipline","status","submitted_by","reviewer","date_submitted","date_required","date_returned","wbs_id","activity_id","link","attachments","comments"]

def _rows_to_csv(fields: List[str], rows: List[Dict[str, Any]]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for r in rows:
        r = dict(r)
        # attachments -> CSV
        if "attachments" in r and isinstance(r["attachments"], list):
            r["attachments"] = "; ".join(r["attachments"])
        w.writerow(r)
    return sio.getvalue().encode("utf-8")

def _csv_to_rfi(uploaded) -> List[RFIItem]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[RFIItem] = []
        for i, row in enumerate(rd, start=1):
            out.append(RFIItem(
                id=(row.get("id") or f"RFI-{i:03d}").strip(),
                subject=(row.get("subject") or "").strip(),
                discipline=(row.get("discipline") or "Architecture").strip(),
                spec_ref=(row.get("spec_ref") or "").strip(),
                drawing_ref=(row.get("drawing_ref") or "").strip(),
                question=(row.get("question") or "").strip(),
                status=(row.get("status") or "Open").strip(),
                priority=(row.get("priority") or "Normal").strip(),
                asked_by=(row.get("asked_by") or "").strip(),
                asked_to=(row.get("asked_to") or "").strip(),
                date_sent=_safe_date_str(row.get("date_sent")),
                date_due=_safe_date_str(row.get("date_due")),
                date_answered=_safe_date_str(row.get("date_answered")),
                response_summary=(row.get("response_summary") or "").strip(),
                wbs_id=(row.get("wbs_id") or "").strip(),
                activity_id=(row.get("activity_id") or "").strip(),
                link=(row.get("link") or "").strip(),
                attachments=_listify(row.get("attachments") or ""),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (RFI): {e}")
        return []

def _csv_to_submittal(uploaded) -> List[SubmittalItem]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[SubmittalItem] = []
        for i, row in enumerate(rd, start=1):
            out.append(SubmittalItem(
                id=(row.get("id") or f"SUB-{i:03d}").strip(),
                package=(row.get("package") or "").strip(),
                spec_section=(row.get("spec_section") or "").strip(),
                title=(row.get("title") or "").strip(),
                discipline=(row.get("discipline") or "Architecture").strip(),
                status=(row.get("status") or "Submitted").strip(),
                submitted_by=(row.get("submitted_by") or "").strip(),
                reviewer=(row.get("reviewer") or "").strip(),
                date_submitted=_safe_date_str(row.get("date_submitted")),
                date_required=_safe_date_str(row.get("date_required")),
                date_returned=_safe_date_str(row.get("date_returned")),
                wbs_id=(row.get("wbs_id") or "").strip(),
                activity_id=(row.get("activity_id") or "").strip(),
                link=(row.get("link") or "").strip(),
                attachments=_listify(row.get("attachments") or ""),
                comments=(row.get("comments") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Submittal): {e}")
        return []

# ---------------- metrics ----------------
def _rfi_metrics(rows: List[RFIItem]) -> Dict[str, Any]:
    today = date.today()
    open_cnt = 0
    overdue = 0
    turn_days = []
    for r in rows:
        if r.status in ("Closed", "Answered"):
            sent = _parse_date(r.date_sent)
            ans  = _parse_date(r.date_answered)
            if sent and ans:
                turn_days.append((ans - sent).days)
        else:
            open_cnt += 1
            due = _parse_date(r.date_due)
            ans = _parse_date(r.date_answered)
            if due and (ans is None) and due < today:
                overdue += 1
    avg_turn = round(sum(turn_days)/len(turn_days), 1) if turn_days else 0.0
    return {"total": len(rows), "open": open_cnt, "overdue": overdue, "avg_turn_days": avg_turn}

def _sub_metrics(rows: List[SubmittalItem]) -> Dict[str, Any]:
    today = date.today()
    open_cnt = 0
    overdue = 0
    turn_days = []
    for r in rows:
        if r.status in ("Approved", "Approved as Noted", "Rejected", "Closed"):
            sub = _parse_date(r.date_submitted)
            ret = _parse_date(r.date_returned)
            if sub and ret:
                turn_days.append((ret - sub).days)
        else:
            open_cnt += 1
            req = _parse_date(r.date_required)
            ret = _parse_date(r.date_returned)
            if req and (ret is None) and req < today:
                overdue += 1
    avg_turn = round(sum(turn_days)/len(turn_days), 1) if turn_days else 0.0
    return {"total": len(rows), "open": open_cnt, "overdue": overdue, "avg_turn_days": avg_turn}

# ---------------- UI: RFI editor ----------------
def _rfi_tab(pid: str, phid: str):
    st.caption("Request for Information (RFI) Log")

    latest = get_latest(pid, ART_RFI, phid)
    rows = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [RFIItem(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} RFIs")

    state_key = _keyify("rfi_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    # Import/Export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import RFI CSV", type=["csv"], key=_keyify("rfi_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_rfi(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} RFIs.")
        with c2:
            st.download_button(
                "Download RFI CSV",
                data=_rows_to_csv(RFI_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_rfi_log.csv",
                mime="text/csv",
                key=_keyify("rfi_exp", pid, phid),
            )

    # Filters
    f1, f2, f3, f4 = st.columns([1,1,1,2])
    with f1:
        filt_disc = st.multiselect("Discipline", options=DISCIPLINES, default=[], key=_keyify("rfi_f_disc", pid, phid))
    with f2:
        filt_stat = st.multiselect("Status", options=RFI_STATUSES, default=[], key=_keyify("rfi_f_stat", pid, phid))
    with f3:
        filt_prio = st.multiselect("Priority", options=RFI_PRIORITIES, default=[], key=_keyify("rfi_f_prio", pid, phid))
    with f4:
        search = st.text_input("Search", "", key=_keyify("rfi_f_txt", pid, phid))

    def _pass(r: RFIItem) -> bool:
        if filt_disc and r.discipline not in filt_disc: return False
        if filt_stat and r.status not in filt_stat: return False
        if filt_prio and r.priority not in filt_prio: return False
        if search:
            s = search.lower()
            blob = " ".join([
                r.id, r.subject, r.discipline, r.spec_ref, r.drawing_ref, r.question,
                r.status, r.priority, r.asked_by, r.asked_to, r.response_summary,
                r.wbs_id, r.activity_id, r.link, ", ".join(r.attachments or []), r.notes
            ]).lower()
            if s not in blob: return False
        return True

    # KPIs
    kpi = _rfi_metrics(st.session_state[state_key])
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total", kpi["total"])
    with k2: st.metric("Open", kpi["open"])
    with k3: st.metric("Overdue", kpi["overdue"])
    with k4: st.metric("Avg answer days", kpi["avg_turn_days"])

    # add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add RFI", key=_keyify("rfi_add", pid, phid)):
            next_num = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(RFIItem(id=f"RFI-{next_num:03d}"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("rfi_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # editor
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass(r):
            continue
        with st.expander(f"{r.id} · {r.subject or 'RFI'} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("RFI ID", r.id, key=_keyify("rfi_id", pid, phid, idx))
                r.subject = st.text_input("Subject", r.subject, key=_keyify("rfi_subject", pid, phid, idx))
                r.discipline = st.selectbox("Discipline", DISCIPLINES,
                                            index=max(0, DISCIPLINES.index(r.discipline) if r.discipline in DISCIPLINES else 0),
                                            key=_keyify("rfi_disc", pid, phid, idx))
                r.priority = st.selectbox("Priority", RFI_PRIORITIES,
                                          index=max(0, RFI_PRIORITIES.index(r.priority) if r.priority in RFI_PRIORITIES else 0),
                                          key=_keyify("rfi_pri", pid, phid, idx))
            with c2:
                r.status = st.selectbox("Status", RFI_STATUSES,
                                        index=max(0, RFI_STATUSES.index(r.status) if r.status in RFI_STATUSES else 0),
                                        key=_keyify("rfi_stat", pid, phid, idx))
                r.asked_by = st.text_input("Asked by", r.asked_by, key=_keyify("rfi_aby", pid, phid, idx))
                r.asked_to = st.text_input("Asked to", r.asked_to, key=_keyify("rfi_ato", pid, phid, idx))
            with c3:
                r.date_sent = st.text_input("Date sent (YYYY-MM-DD)", r.date_sent, key=_keyify("rfi_sent", pid, phid, idx))
                r.date_due = st.text_input("Due (YYYY-MM-DD)", r.date_due, key=_keyify("rfi_due", pid, phid, idx))
                r.date_answered = st.text_input("Date answered (YYYY-MM-DD)", r.date_answered, key=_keyify("rfi_ans", pid, phid, idx))

            r.spec_ref = st.text_input("Spec ref", r.spec_ref, key=_keyify("rfi_spec", pid, phid, idx))
            r.drawing_ref = st.text_input("Drawing ref", r.drawing_ref, key=_keyify("rfi_draw", pid, phid, idx))
            r.question = st.text_area("Question", r.question, key=_keyify("rfi_q", pid, phid, idx))
            r.response_summary = st.text_area("Response summary", r.response_summary, key=_keyify("rfi_resp", pid, phid, idx))

            c4, c5, c6 = st.columns([1,1,1])
            with c4:
                r.wbs_id = st.text_input("WBS ID (optional)", r.wbs_id, key=_keyify("rfi_wbs", pid, phid, idx))
            with c5:
                r.activity_id = st.text_input("Activity ID (optional)", r.activity_id, key=_keyify("rfi_act", pid, phid, idx))
            with c6:
                r.link = st.text_input("Link (optional)", r.link, key=_keyify("rfi_link", pid, phid, idx))

            attach_raw = st.text_area("Attachments (comma/newline)", ", ".join(r.attachments or []),
                                      key=_keyify("rfi_att", pid, phid, idx))
            r.attachments = _listify(attach_raw)
            r.notes = st.text_area("Notes", r.notes, key=_keyify("rfi_notes", pid, phid, idx))

    st.divider()
    # save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save as Draft (RFI)", key=_keyify("rfi_save_draft", pid, phid)):
            save_artifact(pid, phid, "Engineering", ART_RFI, payload, status="Draft")
            st.success("RFI_Log saved (Draft).")
    with right:
        if st.button("Save as Pending (RFI)", key=_keyify("rfi_save_pend", pid, phid)):
            save_artifact(pid, phid, "Engineering", ART_RFI, payload, status="Pending")
            st.success("RFI_Log saved (Pending).")

# ---------------- UI: Submittal editor ----------------
def _submittal_tab(pid: str, phid: str):
    st.caption("Submittal Log")

    latest = get_latest(pid, ART_SUB, phid)
    rows = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [SubmittalItem(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} submittals")

    state_key = _keyify("sub_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import Submittal CSV", type=["csv"], key=_keyify("sub_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_submittal(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} submittals.")
        with c2:
            st.download_button(
                "Download Submittal CSV",
                data=_rows_to_csv(SUB_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_submittal_log.csv",
                mime="text/csv",
                key=_keyify("sub_exp", pid, phid),
            )

    # Filters
    f1, f2, f3 = st.columns([1,1,2])
    with f1:
        filt_disc = st.multiselect("Discipline", options=DISCIPLINES, default=[], key=_keyify("sub_f_disc", pid, phid))
    with f2:
        filt_stat = st.multiselect("Status", options=SUB_STATUSES, default=[], key=_keyify("sub_f_stat", pid, phid))
    with f3:
        search = st.text_input("Search", "", key=_keyify("sub_f_txt", pid, phid))

    def _pass(r: SubmittalItem) -> bool:
        if filt_disc and r.discipline not in filt_disc: return False
        if filt_stat and r.status not in filt_stat: return False
        if search:
            s = search.lower()
            blob = " ".join([
                r.id, r.package, r.spec_section, r.title, r.discipline, r.status,
                r.submitted_by, r.reviewer, r.wbs_id, r.activity_id, r.link,
                ", ".join(r.attachments or []), r.comments
            ]).lower()
            if s not in blob: return False
        return True

    # KPIs
    kpi = _sub_metrics(st.session_state[state_key])
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total", kpi["total"])
    with k2: st.metric("Open", kpi["open"])
    with k3: st.metric("Overdue", kpi["overdue"])
    with k4: st.metric("Avg return days", kpi["avg_turn_days"])

    # add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add Submittal", key=_keyify("sub_add", pid, phid)):
            next_num = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(SubmittalItem(id=f"SUB-{next_num:03d}"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("sub_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # editor
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass(r):
            continue
        with st.expander(f"{r.id} · {r.title or r.package or 'Submittal'} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("Submittal ID", r.id, key=_keyify("sub_id", pid, phid, idx))
                r.package = st.text_input("Package", r.package, key=_keyify("sub_pkg", pid, phid, idx))
                r.spec_section = st.text_input("Spec section", r.spec_section, key=_keyify("sub_spec", pid, phid, idx))
                r.title = st.text_input("Title", r.title, key=_keyify("sub_title", pid, phid, idx))
            with c2:
                r.discipline = st.selectbox("Discipline", DISCIPLINES,
                                            index=max(0, DISCIPLINES.index(r.discipline) if r.discipline in DISCIPLINES else 0),
                                            key=_keyify("sub_disc", pid, phid, idx))
                r.status = st.selectbox("Status", SUB_STATUSES,
                                        index=max(0, SUB_STATUSES.index(r.status) if r.status in SUB_STATUSES else 0),
                                        key=_keyify("sub_stat", pid, phid, idx))
                r.reviewer = st.text_input("Reviewer", r.reviewer, key=_keyify("sub_rev", pid, phid, idx))
            with c3:
                r.submitted_by = st.text_input("Submitted by", r.submitted_by, key=_keyify("sub_sby", pid, phid, idx))
                r.date_submitted = st.text_input("Date submitted (YYYY-MM-DD)", r.date_submitted, key=_keyify("sub_dsub", pid, phid, idx))
                r.date_required = st.text_input("Date required (YYYY-MM-DD)", r.date_required, key=_keyify("sub_dreq", pid, phid, idx))
                r.date_returned = st.text_input("Date returned (YYYY-MM-DD)", r.date_returned, key=_keyify("sub_dret", pid, phid, idx))

            c4, c5, c6 = st.columns([1,1,1])
            with c4:
                r.wbs_id = st.text_input("WBS ID (optional)", r.wbs_id, key=_keyify("sub_wbs", pid, phid, idx))
            with c5:
                r.activity_id = st.text_input("Activity ID (optional)", r.activity_id, key=_keyify("sub_act", pid, phid, idx))
            with c6:
                r.link = st.text_input("Link (optional)", r.link, key=_keyify("sub_link", pid, phid, idx))

            attach_raw = st.text_area("Attachments (comma/newline)", ", ".join(r.attachments or []),
                                      key=_keyify("sub_att", pid, phid, idx))
            r.attachments = _listify(attach_raw)
            r.comments = st.text_area("Comments", r.comments, key=_keyify("sub_comments", pid, phid, idx))

    st.divider()
    # save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save as Draft (Submittals)", key=_keyify("sub_save_draft", pid, phid)):
            save_artifact(pid, phid, "Engineering", ART_SUB, payload, status="Draft")
            st.success("Submittal_Log saved (Draft).")
    with right:
        if st.button("Save as Pending (Submittals)", key=_keyify("sub_save_pend", pid, phid)):
            save_artifact(pid, phid, "Engineering", ART_SUB, payload, status="Pending")
            st.success("Submittal_Log saved (Pending).")

# ---------------- main entry ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("RFI & Submittals")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    t1, t2 = st.tabs(["RFI Log", "Submittal Log"])
    with t1:
        _rfi_tab(pid, phid)
    with t2:
        _submittal_tab(pid, phid)
