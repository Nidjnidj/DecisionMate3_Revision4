# workflows/pm_arch_construction/clash_log.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import date, datetime

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE   = "Clash_Log"
WORKSTREAM = "Design"

# ---------- util ----------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_date(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def _days(a: str, b: str) -> Optional[int]:
    try:
        da = datetime.strptime(a, "%Y-%m-%d").date()
        db = datetime.strptime(b, "%Y-%m-%d").date()
        return (db - da).days
    except Exception:
        return None

def _listify(raw: str) -> List[str]:
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]

# ---------- dataclass ----------
SEVERITIES = ["Low", "Medium", "High", "Critical"]
STATUSES   = ["Open", "In Review", "Resolved", "Deferred"]

@dataclass
class ClashItem:
    id: str
    title: str = ""
    description: str = ""
    location: str = ""     # room/area
    grid: str = ""         # grid ref
    level: str = ""        # floor/level
    discipline: str = ""   # Arch/Struct/MEP/etc
    severity: str = "Medium"
    status: str = "Open"
    assigned_to: str = ""
    due_date: str = ""     # ISO
    screenshot: str = ""   # url or path
    attachments: List[str] = None
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()+"Z"
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "grid": self.grid,
            "level": self.level,
            "discipline": self.discipline,
            "severity": self.severity,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "due_date": _safe_date(self.due_date),
            "screenshot": self.screenshot,
            "attachments": list(self.attachments or []),
            "notes": self.notes,
            "created_at": self.created_at or now,
            "updated_at": now,
        }

FIELDS = [
    "id","title","description","location","grid","level","discipline",
    "severity","status","assigned_to","due_date","screenshot","attachments",
    "notes","created_at","updated_at"
]

# ---------- CSV I/O ----------
def _csv_write(rows: List[Dict[str, Any]]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        row = dict(r)
        if isinstance(row.get("attachments"), list):
            row["attachments"] = "; ".join(row["attachments"])
        w.writerow({k: row.get(k, "") for k in FIELDS})
    return sio.getvalue().encode("utf-8")

def _csv_read(file) -> List[ClashItem]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[ClashItem] = []
        for i, r in enumerate(rd, 1):
            out.append(ClashItem(
                id=(r.get("id") or f"CL-{i:04d}").strip(),
                title=(r.get("title") or "").strip(),
                description=(r.get("description") or "").strip(),
                location=(r.get("location") or "").strip(),
                grid=(r.get("grid") or "").strip(),
                level=(r.get("level") or "").strip(),
                discipline=(r.get("discipline") or "").strip(),
                severity=(r.get("severity") or "Medium").strip() or "Medium",
                status=(r.get("status") or "Open").strip() or "Open",
                assigned_to=(r.get("assigned_to") or "").strip(),
                due_date=_safe_date(r.get("due_date")),
                screenshot=(r.get("screenshot") or "").strip(),
                attachments=_listify(r.get("attachments") or ""),
                notes=(r.get("notes") or "").strip(),
                created_at=_safe_date(r.get("created_at")) or "",
                updated_at=_safe_date(r.get("updated_at")) or "",
            ))
        return out
    except Exception as e:
        st.error(f"Clash CSV parse error: {e}")
        return []

# ---------- Metrics ----------
def _metrics(items: List[ClashItem]) -> Dict[str, Any]:
    today = date.today().isoformat()
    open_cnt = sum(1 for it in items if it.status in ("Open","In Review"))
    resolved = sum(1 for it in items if it.status == "Resolved")
    overdue = 0
    for it in items:
        if it.status in ("Open","In Review") and it.due_date:
            d = _days(today, _safe_date(it.due_date))
            if isinstance(d, int) and d < 0:
                overdue += 1
    return {"open": open_cnt, "resolved": resolved, "overdue": overdue}

# ---------- Main ----------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Clash Log")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    # Load latest artifact
    latest = get_latest(pid, ART_TYPE, phid)
    init_rows: List[ClashItem] = []
    if latest:
        init_rows = [ClashItem(**r) for r in (latest.get("data", {}) or {}).get("rows", []) if r.get("id")]

    rows_key = _keyify("clash_rows", pid, phid)
    if rows_key not in st.session_state:
        st.session_state[rows_key] = init_rows or [
            ClashItem(id="CL-0001", title="Duct vs Beam at Grid B4",
                      description="Supply duct clashes with beam web",
                      location="Zone B", grid="B4", level="L3",
                      discipline="MEP/STRUCT", severity="High", status="Open",
                      assigned_to="Coord Team", due_date=(date.today()).isoformat(),
                      notes="Check duct drop or beam cope."),
        ]

    # Import / Export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import CSV", type=["csv"], key=_keyify("clash_imp", pid, phid))
            if up is not None:
                parsed = _csv_read(up)
                if parsed:
                    st.session_state[rows_key] = parsed
                    st.success(f"Imported {len(parsed)} clashes.")
        with c2:
            st.download_button(
                "Download CSV",
                data=_csv_write([x.to_dict() for x in st.session_state[rows_key]]),
                file_name=f"{pid}_{phid}_clash_log.csv",
                mime="text/csv",
                key=_keyify("clash_exp", pid, phid),
            )

    # Metrics
    m = _metrics(st.session_state[rows_key])
    a, b, c = st.columns(3)
    with a: st.metric("Open",     m["open"])
    with b: st.metric("Resolved", m["resolved"])
    with c: st.metric("Overdue",  m["overdue"])

    # Filters
    # collect known disciplines from current rows
    known_disc = sorted({(x.discipline or "").strip() for x in st.session_state[rows_key]} - {""})
    f1, f2, f3, f4 = st.columns([2,1,1,1])
    with f1:
        f_text = st.text_input("Filter text (title/desc/location/grid/level/assignee)",
                               key=_keyify("clash_ft", pid, phid))
    with f2:
        f_status = st.multiselect("Status", STATUSES, default=["Open","In Review"],
                                  key=_keyify("clash_st", pid, phid))
    with f3:
        f_sev = st.multiselect("Severity", SEVERITIES, default=SEVERITIES,
                               key=_keyify("clash_sv", pid, phid))
    with f4:
        f_disc = st.multiselect("Discipline", known_disc, default=known_disc,
                                key=_keyify("clash_dc", pid, phid))

    g1, g2 = st.columns(2)
    with g1:
        due_after  = st.text_input("Due after (YYYY-MM-DD)", key=_keyify("clash_da", pid, phid))
    with g2:
        due_before = st.text_input("Due before (YYYY-MM-DD)", key=_keyify("clash_db", pid, phid))

    def _visible(x: ClashItem) -> bool:
        txt = (f_text or "").lower().strip()
        if txt:
            blob = " ".join([x.id, x.title, x.description, x.location, x.grid, x.level, x.assigned_to]).lower()
            if txt not in blob:
                return False
        if f_status and x.status not in f_status: return False
        if f_sev and x.severity not in f_sev: return False
        if f_disc and (x.discipline or "") not in f_disc: return False
        d = _safe_date(x.due_date)
        if due_after and d and _days(_safe_date(due_after), d) is not None:
            if _days(_safe_date(due_after), d) < 0:  # d < after
                return False
        if due_before and d and _days(d, _safe_date(due_before)) is not None:
            if _days(d, _safe_date(due_before)) < 0:  # before < d
                return False
        return True

    # Add/Remove
    aa, bb = st.columns([1,1])
    with aa:
        if st.button("➕ Add clash", key=_keyify("clash_add", pid, phid)):
            n = len(st.session_state[rows_key]) + 1
            st.session_state[rows_key].append(ClashItem(id=f"CL-{n:04d}"))
    with bb:
        if st.button("🗑️ Remove last", key=_keyify("clash_del", pid, phid)):
            if st.session_state[rows_key]:
                st.session_state[rows_key].pop()

    # Editors
    for i, cl in enumerate(st.session_state[rows_key]):
        if not _visible(cl): 
            continue
        overdue_flag = False
        if cl.status in ("Open","In Review") and cl.due_date:
            dd = _days(date.today().isoformat(), _safe_date(cl.due_date))
            overdue_flag = isinstance(dd, int) and dd < 0

        title = cl.title or cl.id
        if overdue_flag:
            title += " · ⚠️ overdue"

        with st.expander(title, expanded=False):
            r1, r2, r3 = st.columns([1,1,1])
            with r1:
                cl.id          = st.text_input("ID", cl.id, key=_keyify("cl_id", pid, phid, i))
                cl.title       = st.text_input("Title", cl.title, key=_keyify("cl_ti", pid, phid, i))
                cl.description = st.text_area("Description", cl.description, key=_keyify("cl_de", pid, phid, i))
                cl.notes       = st.text_area("Notes", cl.notes, key=_keyify("cl_no", pid, phid, i))
            with r2:
                cl.location    = st.text_input("Location/Room", cl.location, key=_keyify("cl_lo", pid, phid, i))
                cl.grid        = st.text_input("Grid", cl.grid, key=_keyify("cl_gr", pid, phid, i))
                cl.level       = st.text_input("Level/Floor", cl.level, key=_keyify("cl_lv", pid, phid, i))
                cl.discipline  = st.text_input("Discipline", cl.discipline, key=_keyify("cl_di", pid, phid, i))
            with r3:
                cl.severity    = st.selectbox("Severity", SEVERITIES, index=max(0, SEVERITIES.index(cl.severity) if cl.severity in SEVERITIES else 1),
                                              key=_keyify("cl_sv", pid, phid, i))
                cl.status      = st.selectbox("Status", STATUSES, index=max(0, STATUSES.index(cl.status) if cl.status in STATUSES else 0),
                                              key=_keyify("cl_st", pid, phid, i))
                cl.assigned_to = st.text_input("Assigned To", cl.assigned_to, key=_keyify("cl_as", pid, phid, i))
                cl.due_date    = st.text_input("Due (YYYY-MM-DD)", cl.due_date, key=_keyify("cl_du", pid, phid, i))
                cl.screenshot  = st.text_input("Screenshot URL", cl.screenshot, key=_keyify("cl_sc", pid, phid, i))
                cl.attachments = _listify(st.text_area("Attachments (comma/newline)",
                                                       ", ".join(cl.attachments or []),
                                                       key=_keyify("cl_at", pid, phid, i)))

    st.divider()
    payload = {"rows": [x.to_dict() for x in st.session_state[rows_key]],
               "saved_at": datetime.utcnow().isoformat() + "Z"}
    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("Save Clash Log (Draft)", key=_keyify("cl_save_d", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
            st.success("Clash Log saved (Draft).")
    with s2:
        if st.button("Save Clash Log (Pending)", key=_keyify("cl_save_p", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            st.success("Clash Log saved (Pending).")
    with s3:
        if st.button("Save & Approve Clash Log", key=_keyify("cl_save_a", pid, phid)):
            rec = save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            try:
                from artifact_registry import approve_artifact
                approve_artifact(pid, rec.get("artifact_id"))
            except Exception:
                pass
            st.success("Clash Log saved and Approved.")
