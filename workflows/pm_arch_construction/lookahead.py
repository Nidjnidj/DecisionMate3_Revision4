# workflows/pm_arch_construction/lookahead.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE = "Lookahead_Plan"

STATUSES = ["Planned", "Committed", "Done", "Blocked", "Deferred"]

# ------------- helpers -------------
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
    return s

def _parse_date(s: str | None) -> Optional[date]:
    s = _safe_date_str(s)
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())

def _weeks(start_monday: date, n: int) -> List[date]:
    return [start_monday + timedelta(days=7*i) for i in range(max(1, n))]

# ------------- data -------------
@dataclass
class PlanRow:
    id: str
    activity_id: str = ""
    activity_name: str = ""
    week_start: str = ""     # YYYY-MM-DD (Monday)
    status: str = "Planned"  # Planned/Committed/Done/Blocked/Deferred
    crew: str = ""
    qty_planned: float = 0.0
    qty_done: float = 0.0
    constraints: str = ""    # e.g., "Permit X, Material Y"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "activity_name": self.activity_name,
            "week_start": _safe_date_str(self.week_start),
            "status": self.status,
            "crew": self.crew,
            "qty_planned": float(self.qty_planned),
            "qty_done": float(self.qty_done),
            "constraints": self.constraints,
            "notes": self.notes,
        }

CSV_FIELDS = ["id","activity_id","activity_name","week_start","status","crew","qty_planned","qty_done","constraints","notes"]

def _rows_to_csv(rows: List[PlanRow]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=CSV_FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow(r.to_dict())
    return sio.getvalue().encode("utf-8")

def _csv_to_rows(uploaded) -> List[PlanRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[PlanRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(PlanRow(
                id=(row.get("id") or f"PLAN-{i:03d}").strip(),
                activity_id=(row.get("activity_id") or "").strip(),
                activity_name=(row.get("activity_name") or "").strip(),
                week_start=_safe_date_str(row.get("week_start")),
                status=(row.get("status") or "Planned").strip(),
                crew=(row.get("crew") or "").strip(),
                qty_planned=float((row.get("qty_planned") or "0").replace(",", "")),
                qty_done=float((row.get("qty_done") or "0").replace(",", "")),
                constraints=(row.get("constraints") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return []

# ------------- metrics -------------
def _ppc(rows: List[PlanRow], horizon: List[date]) -> Dict[str, Any]:
    # PPC = Done / Committed (count), per-week and overall
    week_ppc: Dict[str, Dict[str, float]] = {}
    total_comm, total_done = 0, 0
    for w in horizon:
        wk = w.isoformat()
        rws = [r for r in rows if _parse_date(r.week_start) == w]
        committed = sum(1 for r in rws if r.status in ("Committed", "Done"))
        done = sum(1 for r in rws if r.status == "Done")
        pct = round(done * 100.0 / committed, 1) if committed else 0.0
        week_ppc[wk] = {"committed": committed, "done": done, "ppc": pct}
        total_comm += committed; total_done += done
    overall = round(total_done * 100.0 / total_comm, 1) if total_comm else 0.0
    blocked = sum(1 for r in rows if r.status == "Blocked")
    return {"weeks": week_ppc, "overall_ppc": overall, "committed": total_comm, "done": total_done, "blocked": blocked}

# ------------- main ui -------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("2–6 Week Lookahead Planner")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    # Try to read schedule to suggest activities
    sched = get_latest(pid, "Schedule_Network", phid)
    acts: List[Dict[str, Any]] = []
    crit_ids: List[str] = []
    if sched:
        data = sched.get("data", {}) or {}
        acts = list(data.get("activities", []))
        crit_ids = list(data.get("critical_path_ids", []))
        st.caption(f"Schedule found: {len(acts)} activities · critical path len={len(crit_ids)}")
    else:
        st.caption("No Schedule_Network found. You can still plan with free text activities.")

    # Horizon picker
    today = date.today()
    start_monday = _monday(today)
    default_weeks = 4
    colH1, colH2 = st.columns([1,1])
    with colH1:
        start = st.date_input("Start week (Monday)", value=start_monday, key=_keyify("lh_start", pid, phid))
        start = _monday(start)
    with colH2:
        weeks = st.slider("Horizon (weeks)", 2, 6, default_weeks, key=_keyify("lh_weeks", pid, phid))
    horizon = _weeks(start, weeks)

    # Activity seeding
    with st.expander("🔎 Seed from schedule", expanded=False):
        if acts:
            ids_labels = [f"{a.get('id','?')} · {a.get('name','')}" for a in acts]
            selected = st.multiselect("Select activities to seed",
                                      options=ids_labels,
                                      default=[f"{aid} · {next((a.get('name','') for a in acts if a.get('id')==aid), '')}" for aid in crit_ids[:5]],
                                      key=_keyify("lh_pick", pid, phid))
            seed_week = st.selectbox("Seed into week", [w.isoformat() for w in horizon], index=0, key=_keyify("lh_pick_week", pid, phid))
            if st.button("Seed selected", key=_keyify("lh_seed_sel", pid, phid)):
                rows = st.session_state[_keyify("lh_rows", pid, phid)]
                next_num = len(rows) + 1
                for lab in selected:
                    act_id = lab.split(" · ")[0]
                    act_nm = lab.split(" · ", 1)[1] if " · " in lab else ""
                    rows.append(PlanRow(id=f"PLAN-{next_num:03d}", activity_id=act_id, activity_name=act_nm,
                                        week_start=seed_week, status="Committed"))
                    next_num += 1
                st.success(f"Seeded {len(selected)} row(s).")
        else:
            st.info("No activities available to seed. Create a Schedule first or add rows manually.")

    # Load latest artifact rows (if any)
    latest = get_latest(pid, ART_TYPE, phid)
    initial_rows: List[PlanRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        initial_rows = [PlanRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(initial_rows)} plan rows")

    # State rows
    state_key = _keyify("lh_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = initial_rows

    # Import / Export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import Lookahead CSV", type=["csv"], key=_keyify("lh_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_rows(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} plan rows.")
        with c2:
            st.download_button(
                "Download Lookahead CSV",
                data=_rows_to_csv(st.session_state[state_key]),
                file_name=f"{pid}_{phid}_lookahead.csv",
                mime="text/csv",
                key=_keyify("lh_exp", pid, phid),
            )

    st.divider()

    # Quick add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add row", key=_keyify("lh_add", pid, phid)):
            next_num = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(PlanRow(id=f"PLAN-{next_num:03d}", week_start=start.isoformat()))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("lh_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Week sections
    for w in horizon:
        wk = w.isoformat()
        st.markdown(f"#### Week of {wk}")
        wk_rows = [r for r in st.session_state[state_key] if _parse_date(r.week_start) == w]
        if not wk_rows:
            st.caption("No rows in this week.")
        for idx, r in enumerate([r for r in st.session_state[state_key] if _parse_date(r.week_start) == w]):
            with st.expander(f"{r.id} · {r.activity_name or r.activity_id or 'Activity'} · {r.status}", expanded=False):
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    r.id = st.text_input("Row ID", r.id, key=_keyify("lh_id", pid, phid, wk, idx))
                    r.week_start = st.text_input("Week start (YYYY-MM-DD)", r.week_start or wk, key=_keyify("lh_wk", pid, phid, wk, idx))
                    r.status = st.selectbox("Status", STATUSES,
                                            index=max(0, STATUSES.index(r.status) if r.status in STATUSES else 0),
                                            key=_keyify("lh_stat", pid, phid, wk, idx))
                with c2:
                    r.activity_id = st.text_input("Activity ID", r.activity_id, key=_keyify("lh_actid", pid, phid, wk, idx))
                    r.activity_name = st.text_input("Activity name", r.activity_name, key=_keyify("lh_actnm", pid, phid, wk, idx))
                    r.crew = st.text_input("Crew", r.crew, key=_keyify("lh_crew", pid, phid, wk, idx))
                with c3:
                    r.qty_planned = float(st.text_input("Qty planned", f"{r.qty_planned}", key=_keyify("lh_qp", pid, phid, wk, idx)).replace(",", "") or 0)
                    r.qty_done = float(st.text_input("Qty done", f"{r.qty_done}", key=_keyify("lh_qd", pid, phid, wk, idx)).replace(",", "") or 0)
                r.constraints = st.text_area("Constraints (comma/notes)", r.constraints, key=_keyify("lh_con", pid, phid, wk, idx))
                r.notes = st.text_area("Notes", r.notes, key=_keyify("lh_notes", pid, phid, wk, idx))

    st.divider()

    # Metrics
    roll = _ppc(st.session_state[state_key], horizon)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Committed (horizon)", roll["committed"])
    with k2: st.metric("Done (horizon)", roll["done"])
    with k3: st.metric("Blocked (horizon)", roll["blocked"])
    with k4: st.metric("Overall PPC", f"{roll['overall_ppc']}%")

    # Per-week PPC small table
    with st.expander("Per-week PPC details", expanded=False):
        for wk, r in roll["weeks"].items():
            st.write(f"- **{wk}** → Committed: {r['committed']}, Done: {r['done']}, PPC: {r['ppc']}%")

    # Save
    payload = {
        "start_monday": start.isoformat(),
        "weeks": weeks,
        "rows": [r.to_dict() for r in st.session_state[state_key]],
        "rollup": roll,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    left, right = st.columns(2)
    with left:
        if st.button("Save as Draft", key=_keyify("lh_save_draft", pid, phid)):
            save_artifact(pid, phid, "Construction", ART_TYPE, payload, status="Draft")
            st.success("Lookahead_Plan saved (Draft).")
    with right:
        if st.button("Save as Pending", key=_keyify("lh_save_pend", pid, phid)):
            save_artifact(pid, phid, "Construction", ART_TYPE, payload, status="Pending")
            st.success("Lookahead_Plan saved (Pending).")
