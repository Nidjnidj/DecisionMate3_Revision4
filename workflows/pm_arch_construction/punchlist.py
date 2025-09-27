# workflows/pm_arch_construction/punchlist.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import date, datetime

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_PUNCH = "Punchlist_Log"

PRIORITIES = ["Low", "Medium", "High", "Critical"]
STATUSES   = ["Open", "In Progress", "Ready for Review", "Closed"]
DISCIPLINES = ["Civil", "Architectural", "Structural", "Mechanical", "Electrical", "Plumbing", "Fire", "Other"]

CURRENCY = "$"  # not used here, but handy if you later add cost/retention columns


# ---------------- helpers ----------------
def _keyify(*parts: Any) -> str:
    """Create a unique Streamlit key (only letters/digits/_)."""
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_date_str(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def _listify(raw: str) -> List[str]:
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]

def _days_between(d1: str, d2: str) -> Optional[int]:
    try:
        a = datetime.strptime(d1, "%Y-%m-%d").date()
        b = datetime.strptime(d2, "%Y-%m-%d").date()
        return (b - a).days
    except Exception:
        return None


# ---------------- dataclass model ----------------
@dataclass
class PunchItem:
    id: str
    title: str = ""
    location: str = ""
    discipline: str = "Other"
    priority: str = "Medium"
    status: str = "Open"
    wbs_ref: str = ""
    raised_by: str = ""
    assignee: str = ""
    raised_date: str = ""      # YYYY-MM-DD
    target_date: str = ""      # YYYY-MM-DD
    close_date: str = ""       # YYYY-MM-DD
    photos: List[str] = None   # URLs or filenames
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "location": self.location,
            "discipline": self.discipline,
            "priority": self.priority,
            "status": self.status,
            "wbs_ref": self.wbs_ref,
            "raised_by": self.raised_by,
            "assignee": self.assignee,
            "raised_date": _safe_date_str(self.raised_date),
            "target_date": _safe_date_str(self.target_date),
            "close_date": _safe_date_str(self.close_date),
            "photos": list(self.photos or []),
            "notes": self.notes,
        }


# ---------------- CSV I/O ----------------
FIELDS = [
    "id", "title", "location", "discipline", "priority", "status", "wbs_ref",
    "raised_by", "assignee", "raised_date", "target_date", "close_date", "photos", "notes"
]

def _rows_to_csv(rows: List[Dict[str, Any]]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        row = dict(r)
        if isinstance(row.get("photos"), list):
            row["photos"] = "; ".join(row["photos"])
        w.writerow({k: row.get(k, "") for k in FIELDS})
    return sio.getvalue().encode("utf-8")

def _csv_to_items(uploaded) -> List[PunchItem]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[PunchItem] = []
        for i, row in enumerate(rd, start=1):
            out.append(PunchItem(
                id=(row.get("id") or f"P-{i:04d}").strip(),
                title=(row.get("title") or "").strip(),
                location=(row.get("location") or "").strip(),
                discipline=(row.get("discipline") or "Other").strip(),
                priority=(row.get("priority") or "Medium").strip(),
                status=(row.get("status") or "Open").strip(),
                wbs_ref=(row.get("wbs_ref") or "").strip(),
                raised_by=(row.get("raised_by") or "").strip(),
                assignee=(row.get("assignee") or "").strip(),
                raised_date=_safe_date_str(row.get("raised_date")),
                target_date=_safe_date_str(row.get("target_date")),
                close_date=_safe_date_str(row.get("close_date")),
                photos=_listify(row.get("photos") or ""),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return []


# ---------------- metrics ----------------
def _metrics(rows: List[PunchItem]) -> Dict[str, Any]:
    today = date.today().isoformat()
    total = len(rows)
    open_count = sum(1 for r in rows if r.status != "Closed")
    closed = sum(1 for r in rows if r.status == "Closed")
    overdue = 0
    ages = []
    ttc = []  # time-to-close

    for r in rows:
        # overdue if not closed and target_date has passed
        if r.status != "Closed" and r.target_date:
            dd = _days_between(r.target_date, today)
            if isinstance(dd, int) and dd < 0:
                # negative means target earlier than today
                overdue += 1
        # age (open)
        if r.status != "Closed" and r.raised_date:
            d = _days_between(r.raised_date, today)
            if isinstance(d, int):
                ages.append(d)
        # time to close
        if r.status == "Closed" and r.raised_date and r.close_date:
            d = _days_between(r.raised_date, r.close_date)
            if isinstance(d, int):
                ttc.append(d)

    avg_age = round(sum(ages) / len(ages), 1) if ages else 0.0
    avg_ttc = round(sum(ttc) / len(ttc), 1) if ttc else 0.0
    return {
        "total": total,
        "open": open_count,
        "closed": closed,
        "overdue": overdue,
        "avg_age": avg_age,
        "avg_ttc": avg_ttc,
    }


# ---------------- main UI ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Punchlist (Closeout)")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    latest = get_latest(pid, ART_PUNCH, phid)
    rows: List[PunchItem] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [PunchItem(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved: **{latest.get('status','Pending')}** · {len(rows)} items")

    state_key = _keyify("punch_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows or [
            PunchItem(id="P-0001", title="Touch-up paint at lobby", location="L1 Lobby",
                      discipline="Architectural", priority="Low", status="Open",
                      raised_by="QAQC", assignee="Painter",
                      raised_date=date.today().isoformat(), target_date=date.today().isoformat()),
            PunchItem(id="P-0002", title="Replace cracked floor tile", location="L2 Corridor",
                      discipline="Architectural", priority="Medium", status="In Progress",
                      raised_by="QAQC", assignee="Tiling Sub",
                      raised_date=date.today().isoformat(), target_date=date.today().isoformat()),
        ]

    # ---------------- Import / Export ----------------
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import Punchlist CSV", type=["csv"], key=_keyify("punch_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_items(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} items.")
        with c2:
            st.download_button(
                "Download Punchlist CSV",
                data=_rows_to_csv([r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_punchlist.csv",
                mime="text/csv",
                key=_keyify("punch_exp", pid, phid),
            )

    # ---------------- KPIs ----------------
    m = _metrics(st.session_state[state_key])
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Total", m["total"])
    with k2: st.metric("Open", m["open"])
    with k3: st.metric("Closed", m["closed"])
    with k4: st.metric("Overdue", m["overdue"])
    with k5: st.metric("Avg Age (open)", m["avg_age"])
    st.caption(f"Average time-to-close (closed): {m['avg_ttc']} days")

    st.divider()

    # ---------------- Filters (local, for editing list) ----------------
    all_assignees = sorted({r.assignee for r in st.session_state[state_key] if r.assignee})
    all_locations = sorted({r.location for r in st.session_state[state_key] if r.location})

    fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
    with fc1:
        f_text = st.text_input("Filter by text (ID/Title/Notes)", key=_keyify("punch_ft", pid, phid))
    with fc2:
        f_status = st.multiselect("Status", STATUSES, default=STATUSES, key=_keyify("punch_fs", pid, phid))
    with fc3:
        f_prio = st.multiselect("Priority", PRIORITIES, default=PRIORITIES, key=_keyify("punch_fp", pid, phid))
    with fc4:
        f_assignee = st.selectbox("Assignee", ["(any)"] + all_assignees, index=0, key=_keyify("punch_fa", pid, phid))

    def _visible(item: PunchItem) -> bool:
        if f_status and item.status not in f_status:
            return False
        if f_prio and item.priority not in f_prio:
            return False
        if f_assignee != "(any)" and item.assignee != f_assignee:
            return False
        tx = (f_text or "").lower().strip()
        if tx:
            blob = " ".join([item.id, item.title, item.location, item.notes]).lower()
            if tx not in blob:
                return False
        return True

    # ---------------- Add / Remove ----------------
    aa, bb = st.columns([1,1])
    with aa:
        if st.button("➕ Add item", key=_keyify("punch_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(
                PunchItem(id=f"P-{n:04d}", raised_date=date.today().isoformat(), target_date=date.today().isoformat())
            )
    with bb:
        if st.button("🗑️ Remove last", key=_keyify("punch_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # ---------------- Editor ----------------
    for idx, r in enumerate(st.session_state[state_key]):
        if not _visible(r):
            continue
        with st.expander(f"{r.id} · {r.title or r.location or r.discipline} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])

            with c1:
                r.id = st.text_input("Punch ID", r.id, key=_keyify("pi_id", pid, phid, idx))
                r.title = st.text_input("Title", r.title, key=_keyify("pi_title", pid, phid, idx))
                r.location = st.text_input("Location", r.location, key=_keyify("pi_loc", pid, phid, idx))
                r.discipline = st.selectbox("Discipline", DISCIPLINES,
                                            index=max(0, DISCIPLINES.index(r.discipline) if r.discipline in DISCIPLINES else 0),
                                            key=_keyify("pi_disc", pid, phid, idx))
            with c2:
                r.priority = st.selectbox("Priority", PRIORITIES,
                                          index=max(0, PRIORITIES.index(r.priority) if r.priority in PRIORITIES else 0),
                                          key=_keyify("pi_prio", pid, phid, idx))
                r.status = st.selectbox("Status", STATUSES,
                                        index=max(0, STATUSES.index(r.status) if r.status in STATUSES else 0),
                                        key=_keyify("pi_stat", pid, phid, idx))
                r.wbs_ref = st.text_input("WBS Ref", r.wbs_ref, key=_keyify("pi_wbs", pid, phid, idx))
                r.raised_by = st.text_input("Raised by", r.raised_by, key=_keyify("pi_rb", pid, phid, idx))
                r.assignee = st.text_input("Assignee", r.assignee, key=_keyify("pi_asg", pid, phid, idx))
            with c3:
                r.raised_date = st.text_input("Raised (YYYY-MM-DD)", r.raised_date or date.today().isoformat(),
                                              key=_keyify("pi_rd", pid, phid, idx))
                r.target_date = st.text_input("Target (YYYY-MM-DD)", r.target_date or "",
                                              key=_keyify("pi_td", pid, phid, idx))
                r.close_date  = st.text_input("Close (YYYY-MM-DD)", r.close_date or "",
                                              key=_keyify("pi_cd", pid, phid, idx))
                r.photos = _listify(st.text_area("Photo links (comma/newline)", ", ".join(r.photos or []),
                                                 key=_keyify("pi_ph", pid, phid, idx)))
            r.notes = st.text_area("Notes", r.notes, key=_keyify("pi_notes", pid, phid, idx))

    st.divider()

    # ---------------- Save ----------------
    payload = {
        "rows": [r.to_dict() for r in st.session_state[state_key]],
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    left, right, approve = st.columns(3)
    with left:
        if st.button("Save Punchlist (Draft)", key=_keyify("punch_save_d", pid, phid)):
            save_artifact(pid, phid, "QAQC", ART_PUNCH, payload, status="Draft")
            st.success("Punchlist saved (Draft).")
    with right:
        if st.button("Save Punchlist (Pending)", key=_keyify("punch_save_p", pid, phid)):
            save_artifact(pid, phid, "QAQC", ART_PUNCH, payload, status="Pending")
            st.success("Punchlist saved (Pending).")
    with approve:
        if st.button("Save & Approve Punchlist", key=_keyify("punch_save_a", pid, phid)):
            rec = save_artifact(pid, phid, "QAQC", ART_PUNCH, payload, status="Pending")
            try:
                from artifact_registry import approve_artifact
                approve_artifact(pid, rec.get("artifact_id"))
            except Exception:
                pass
            st.success("Punchlist saved and Approved.")
