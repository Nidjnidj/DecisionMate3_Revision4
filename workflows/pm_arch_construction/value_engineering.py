# workflows/pm_arch_construction/value_engineering.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import date, datetime

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE   = "VE_Log"
WORKSTREAM = "Engineering"
CURRENCY   = "$"

# ---------------- utils ----------------
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

def _parse_float(x: Any) -> float:
    try:
        return float(str(x).replace(",", "").replace(CURRENCY, "").strip())
    except Exception:
        return 0.0

def _listify(raw: str) -> List[str]:
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]

# ---------------- schema ----------------
STATUSES   = ["Proposed", "In Review", "Accepted", "Rejected", "Implemented"]
DISCIPLINE = ["Architecture", "Structural", "Mechanical", "Electrical", "Plumbing", "Fire", "Civil", "IT/ELV", "Other"]
CATEGORY   = ["Cost", "Functionality", "Maintainability", "Reliability", "Sustainability", "Safety", "Constructability", "Other"]

@dataclass
class VEItem:
    id: str
    title: str = ""
    discipline: str = "Other"
    category: str = "Cost"
    current_design: str = ""
    proposed_change: str = ""
    cost_baseline: float = 0.0     # CAPEX (current)
    cost_proposed: float = 0.0     # CAPEX (proposed)
    opex_delta_y: float = 0.0      # OPEX change per year (negative = saving)
    schedule_delta_d: int = 0      # + saves days (or negative if adds)
    feasibility: int = 3           # 1..5
    benefit: int = 3               # 1..5
    risk: int = 2                  # 1..5
    status: str = "Proposed"
    proposer: str = ""
    owner: str = ""
    decision_date: str = ""        # ISO
    attachments: List[str] = None
    notes: str = ""

    def savings_capex(self) -> float:
        # Positive number means CAPEX saving
        return float(self.cost_baseline) - float(self.cost_proposed)

    def priority_score(self) -> float:
        # Simple 0..100: (benefit * feasibility * 4) - (risk * 5)
        # Keep within 0..100
        raw = (float(self.benefit) * float(self.feasibility) * 4.0) - (float(self.risk) * 5.0)
        return max(0.0, min(100.0, raw))

    def to_dict(self) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat() + "Z"
        return {
            "id": self.id,
            "title": self.title,
            "discipline": self.discipline,
            "category": self.category,
            "current_design": self.current_design,
            "proposed_change": self.proposed_change,
            "cost_baseline": float(self.cost_baseline or 0.0),
            "cost_proposed": float(self.cost_proposed or 0.0),
            "opex_delta_y": float(self.opex_delta_y or 0.0),
            "schedule_delta_d": int(self.schedule_delta_d or 0),
            "feasibility": int(self.feasibility or 0),
            "benefit": int(self.benefit or 0),
            "risk": int(self.risk or 0),
            "status": self.status,
            "proposer": self.proposer,
            "owner": self.owner,
            "decision_date": _safe_date(self.decision_date),
            "attachments": list(self.attachments or []),
            "notes": self.notes,
            # computed
            "capex_saving": float(self.savings_capex()),
            "priority_score": float(self.priority_score()),
            "updated_at": now,
        }

FIELDS = [
    "id","title","discipline","category","current_design","proposed_change",
    "cost_baseline","cost_proposed","capex_saving","opex_delta_y","schedule_delta_d",
    "feasibility","benefit","risk","priority_score",
    "status","proposer","owner","decision_date","attachments","notes","updated_at"
]

# ---------------- CSV I/O ----------------
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

def _csv_read(file) -> List[VEItem]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[VEItem] = []
        for i, r in enumerate(rd, 1):
            it = VEItem(
                id=(r.get("id") or f"VE-{i:04d}").strip(),
                title=(r.get("title") or "").strip(),
                discipline=(r.get("discipline") or "Other").strip(),
                category=(r.get("category") or "Cost").strip(),
                current_design=(r.get("current_design") or "").strip(),
                proposed_change=(r.get("proposed_change") or "").strip(),
                cost_baseline=_parse_float(r.get("cost_baseline")),
                cost_proposed=_parse_float(r.get("cost_proposed")),
                opex_delta_y=_parse_float(r.get("opex_delta_y")),
                schedule_delta_d=int(_parse_float(r.get("schedule_delta_d"))),
                feasibility=int(_parse_float(r.get("feasibility")) or 0) or 0,
                benefit=int(_parse_float(r.get("benefit")) or 0) or 0,
                risk=int(_parse_float(r.get("risk")) or 0) or 0,
                status=(r.get("status") or "Proposed").strip(),
                proposer=(r.get("proposer") or "").strip(),
                owner=(r.get("owner") or "").strip(),
                decision_date=_safe_date(r.get("decision_date")),
                attachments=_listify(r.get("attachments") or ""),
                notes=(r.get("notes") or "").strip(),
            )
            out.append(it)
        return out
    except Exception as e:
        st.error(f"VE CSV parse error: {e}")
        return []

# ---------------- metrics ----------------
def _metrics(items: List[VEItem]) -> Dict[str, Any]:
    total = len(items)
    proposed = sum(1 for x in items if x.status == "Proposed")
    in_review = sum(1 for x in items if x.status == "In Review")
    accepted = sum(1 for x in items if x.status == "Accepted")
    implemented = sum(1 for x in items if x.status == "Implemented")
    rejected = sum(1 for x in items if x.status == "Rejected")
    # savings: consider accepted + implemented as “approved savings”
    capex_sav = sum(x.savings_capex() for x in items if x.status in ("Accepted","Implemented"))
    opex_delta = sum(float(x.opex_delta_y or 0.0) for x in items if x.status in ("Accepted","Implemented"))
    # schedule: sum days for accepted + implemented
    sched_days = sum(int(x.schedule_delta_d or 0) for x in items if x.status in ("Accepted","Implemented"))
    # average priority across all
    ps = [x.priority_score() for x in items]
    avg_priority = round(sum(ps)/len(ps), 1) if ps else 0.0
    return {
        "total": total, "proposed": proposed, "in_review": in_review,
        "accepted": accepted, "implemented": implemented, "rejected": rejected,
        "capex_sav": capex_sav, "opex_delta": opex_delta, "sched_days": sched_days,
        "avg_priority": avg_priority
    }

# ---------------- main ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Value Engineering (VE) Log")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    latest = get_latest(pid, ART_TYPE, phid)
    init_rows: List[VEItem] = []
    if latest:
        init_rows = [VEItem(**r) for r in (latest.get("data", {}) or {}).get("rows", []) if r.get("id")]

    rows_key = _keyify("ve_rows", pid, phid)
    if rows_key not in st.session_state:
        st.session_state[rows_key] = init_rows or [
            VEItem(
                id="VE-0001",
                title="Switch facade cladding to composite panels",
                discipline="Architecture",
                category="Cost",
                current_design="Stone cladding on elevations A/B",
                proposed_change="Composite aluminum panels with similar appearance",
                cost_baseline=800000,
                cost_proposed=620000,
                opex_delta_y=-5000,  # save $5k/y maintenance
                schedule_delta_d=7,  # save a week
                feasibility=4, benefit=4, risk=2,
                status="Proposed",
                proposer="Contractor",
                owner="Architect",
                notes="Confirm fire rating equivalency and warranty terms."
            )
        ]

    # Import / Export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import VE CSV", type=["csv"], key=_keyify("ve_imp", pid, phid))
            if up is not None:
                parsed = _csv_read(up)
                if parsed:
                    st.session_state[rows_key] = parsed
                    st.success(f"Imported {len(parsed)} VE ideas.")
        with c2:
            st.download_button(
                "Download VE CSV",
                data=_csv_write([x.to_dict() for x in st.session_state[rows_key]]),
                file_name=f"{pid}_{phid}_ve_log.csv",
                mime="text/csv",
                key=_keyify("ve_exp", pid, phid),
            )

    # Metrics row
    m = _metrics(st.session_state[rows_key])
    a, b, c, d, e, f, g = st.columns(7)
    with a: st.metric("Total", m["total"])
    with b: st.metric("Proposed", m["proposed"])
    with c: st.metric("Accepted", m["accepted"])
    with d: st.metric("Implemented", m["implemented"])
    with e: st.metric("CAPEX Saving (approved)", f"{CURRENCY}{m['capex_sav']:,.0f}")
    with f: st.metric("OPEX Δ/yr (approved)", f"{CURRENCY}{m['opex_delta']:,.0f}")
    with g: st.metric("Sched. Δ days (approved)", m["sched_days"])
    st.caption(f"Avg priority: {m['avg_priority']} / 100")

    st.divider()

    # Filters
    known_disc = sorted({(x.discipline or "").strip() for x in st.session_state[rows_key]} - {""})
    known_cat  = sorted({(x.category or "").strip() for x in st.session_state[rows_key]} - {""})

    f1, f2, f3, f4 = st.columns([2,1,1,1])
    with f1:
        f_text = st.text_input("Filter text (title/desc/proposer/owner)", key=_keyify("ve_ft", pid, phid))
    with f2:
        f_status = st.multiselect("Status", STATUSES, default=STATUSES, key=_keyify("ve_fs", pid, phid))
    with f3:
        f_disc = st.multiselect("Discipline", known_disc or DISCIPLINE, default=known_disc or DISCIPLINE,
                                key=_keyify("ve_fd", pid, phid))
    with f4:
        f_cat = st.multiselect("Category", known_cat or CATEGORY, default=known_cat or CATEGORY,
                               key=_keyify("ve_fc", pid, phid))
    f5, f6 = st.columns([1,1])
    with f5:
        min_score = st.slider("Min priority score", 0, 100, 0, key=_keyify("ve_minps", pid, phid))
    with f6:
        only_approved = st.checkbox("Only Accepted/Implemented", value=False, key=_keyify("ve_oa", pid, phid))

    def _visible(x: VEItem) -> bool:
        if only_approved and x.status not in ("Accepted","Implemented"):
            return False
        if f_status and x.status not in f_status:
            return False
        if f_disc and (x.discipline or "") not in f_disc:
            return False
        if f_cat and (x.category or "") not in f_cat:
            return False
        if x.priority_score() < float(min_score or 0):
            return False
        txt = (f_text or "").lower().strip()
        if txt:
            blob = " ".join([x.id, x.title, x.current_design, x.proposed_change, x.proposer, x.owner, x.notes]).lower()
            if txt not in blob:
                return False
        return True

    # Add/Remove
    aa, bb = st.columns([1,1])
    with aa:
        if st.button("➕ Add VE idea", key=_keyify("ve_add", pid, phid)):
            n = len(st.session_state[rows_key]) + 1
            st.session_state[rows_key].append(VEItem(id=f"VE-{n:04d}"))
    with bb:
        if st.button("🗑️ Remove last", key=_keyify("ve_del", pid, phid)):
            if st.session_state[rows_key]:
                st.session_state[rows_key].pop()

    # Editors
    for i, it in enumerate(st.session_state[rows_key]):
        if not _visible(it):
            continue

        header = f"{it.id} · {it.title or it.category} · {it.status} · Score {it.priority_score():.0f}"
        with st.expander(header, expanded=False):
            c1, c2, c3 = st.columns([1,1,1])

            with c1:
                it.id          = st.text_input("ID", it.id, key=_keyify("ve_id", pid, phid, i))
                it.title       = st.text_input("Title", it.title, key=_keyify("ve_ti", pid, phid, i))
                it.discipline  = st.selectbox("Discipline", DISCIPLINE,
                                              index=max(0, (DISCIPLINE.index(it.discipline) if it.discipline in DISCIPLINE else DISCIPLINE.index("Other"))),
                                              key=_keyify("ve_di", pid, phid, i))
                it.category    = st.selectbox("Category", CATEGORY,
                                              index=max(0, (CATEGORY.index(it.category) if it.category in CATEGORY else CATEGORY.index("Cost"))),
                                              key=_keyify("ve_ca", pid, phid, i))
                it.status      = st.selectbox("Status", STATUSES,
                                              index=max(0, STATUSES.index(it.status) if it.status in STATUSES else 0),
                                              key=_keyify("ve_st", pid, phid, i))
            with c2:
                it.current_design  = st.text_area("Current Design", it.current_design, key=_keyify("ve_cd", pid, phid, i))
                it.proposed_change = st.text_area("Proposed Change", it.proposed_change, key=_keyify("ve_pc", pid, phid, i))
                it.notes           = st.text_area("Notes", it.notes, key=_keyify("ve_no", pid, phid, i))
            with c3:
                it.cost_baseline   = _parse_float(st.text_input(f"CAPEX Baseline ({CURRENCY})", f"{it.cost_baseline}",
                                                                key=_keyify("ve_cb", pid, phid, i)))
                it.cost_proposed   = _parse_float(st.text_input(f"CAPEX Proposed ({CURRENCY})", f"{it.cost_proposed}",
                                                                key=_keyify("ve_cp", pid, phid, i)))
                it.opex_delta_y    = _parse_float(st.text_input(f"OPEX Δ / year ({CURRENCY})", f"{it.opex_delta_y}",
                                                                key=_keyify("ve_ox", pid, phid, i)))
                it.schedule_delta_d= int(_parse_float(st.text_input("Schedule Δ (days)", f"{it.schedule_delta_d}",
                                                                    key=_keyify("ve_sd", pid, phid, i))))
                it.feasibility     = st.slider("Feasibility (1-5)", 1, 5, int(it.feasibility or 3), key=_keyify("ve_fe", pid, phid, i))
                it.benefit         = st.slider("Benefit (1-5)", 1, 5, int(it.benefit or 3), key=_keyify("ve_be", pid, phid, i))
                it.risk            = st.slider("Risk (1-5)", 1, 5, int(it.risk or 2), key=_keyify("ve_ri", pid, phid, i))
                it.proposer        = st.text_input("Proposer", it.proposer, key=_keyify("ve_pr", pid, phid, i))
                it.owner           = st.text_input("Owner", it.owner, key=_keyify("ve_ow", pid, phid, i))
                it.decision_date   = st.text_input("Decision date (YYYY-MM-DD)", it.decision_date,
                                                   key=_keyify("ve_dd", pid, phid, i))
                it.attachments     = _listify(st.text_area("Attachments (comma/newline)",
                                                           ", ".join(it.attachments or []),
                                                           key=_keyify("ve_at", pid, phid, i)))

            # live computed chips
            capex_sav = it.savings_capex()
            st.caption(
                f"**Computed:** CAPEX saving = {CURRENCY}{capex_sav:,.0f} | "
                f"OPEX Δ/yr = {CURRENCY}{it.opex_delta_y:,.0f} | "
                f"Sched Δ = {it.schedule_delta_d} d | "
                f"Priority Score = {it.priority_score():.0f}/100"
            )

    st.divider()
    payload = {
        "rows": [x.to_dict() for x in st.session_state[rows_key]],
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }

    s1, s2, s3 = st.columns(3)
    with s1:
        if st.button("Save VE Log (Draft)", key=_keyify("ve_save_d", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
            st.success("VE Log saved (Draft).")
    with s2:
        if st.button("Save VE Log (Pending)", key=_keyify("ve_save_p", pid, phid)):
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            st.success("VE Log saved (Pending).")
    with s3:
        if st.button("Save & Approve VE Log", key=_keyify("ve_save_a", pid, phid)):
            rec = save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
            try:
                from artifact_registry import approve_artifact
                approve_artifact(pid, rec.get("artifact_id"))
            except Exception:
                pass
            st.success("VE Log saved and Approved.")
