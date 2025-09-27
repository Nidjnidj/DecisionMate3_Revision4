# workflows/pm_arch_construction/change_orders.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE = "Change_Order_Log"

STATUSES = ["Proposed", "Pending Client", "Approved", "Rejected", "Withdrawn"]
REASONS  = ["Client Request", "Design Change/Error", "Unforeseen Conditions", "Vendor/Sub Change", "Other"]
ORIGINS  = ["RFI", "Submittal", "Site Instruction", "PC/Contingency", "Other"]

# ---------- helpers ----------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _safe_date_str(s: str | None) -> str:
    if not s: return ""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def _parse_float(x: Any) -> float:
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0

def _parse_int(x: Any) -> int:
    try:
        return int(float(str(x).replace(",", "").strip()))
    except Exception:
        return 0

def _listify(raw: str) -> List[str]:
    if not raw: return []
    parts = re.split(r"[,\n;]+", raw)
    return [p.strip() for p in parts if p.strip()]

# ---------- data ----------
@dataclass
class COItem:
    id: str
    title: str = ""
    origin: str = "RFI"           # RFI/Submittal/etc
    reason: str = "Client Request"
    status: str = "Proposed"
    value_usd: float = 0.0
    days_impact: int = 0
    submitted_by: str = ""
    owner_decision_by: str = ""   # approver/responsible
    date_submitted: str = ""      # YYYY-MM-DD
    date_decided: str = ""        # YYYY-MM-DD
    linked_rfis: List[str] = None
    linked_submittals: List[str] = None
    ref: str = ""                 # doc ref / CO form #
    notes: str = ""
    attachments: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "origin": self.origin,
            "reason": self.reason,
            "status": self.status,
            "value_usd": float(self.value_usd),
            "days_impact": int(self.days_impact),
            "submitted_by": self.submitted_by,
            "owner_decision_by": self.owner_decision_by,
            "date_submitted": _safe_date_str(self.date_submitted),
            "date_decided": _safe_date_str(self.date_decided),
            "linked_rfis": list(self.linked_rfis or []),
            "linked_submittals": list(self.linked_submittals or []),
            "ref": self.ref,
            "notes": self.notes,
            "attachments": list(self.attachments or []),
        }

CSV_FIELDS = ["id","title","origin","reason","status","value_usd","days_impact","submitted_by","owner_decision_by","date_submitted","date_decided","linked_rfis","linked_submittals","ref","notes","attachments"]

def _rows_to_csv(rows: List[COItem]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=CSV_FIELDS)
    w.writeheader()
    for r in rows:
        d = r.to_dict()
        d["linked_rfis"] = "; ".join(d["linked_rfis"])
        d["linked_submittals"] = "; ".join(d["linked_submittals"])
        d["attachments"] = "; ".join(d["attachments"])
        w.writerow(d)
    return sio.getvalue().encode("utf-8")

def _csv_to_rows(uploaded) -> List[COItem]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[COItem] = []
        for i, row in enumerate(rd, start=1):
            out.append(COItem(
                id=(row.get("id") or f"CO-{i:03d}").strip(),
                title=(row.get("title") or "").strip(),
                origin=(row.get("origin") or "RFI").strip(),
                reason=(row.get("reason") or "Client Request").strip(),
                status=(row.get("status") or "Proposed").strip(),
                value_usd=_parse_float(row.get("value_usd")),
                days_impact=_parse_int(row.get("days_impact")),
                submitted_by=(row.get("submitted_by") or "").strip(),
                owner_decision_by=(row.get("owner_decision_by") or "").strip(),
                date_submitted=_safe_date_str(row.get("date_submitted")),
                date_decided=_safe_date_str(row.get("date_decided")),
                linked_rfis=_listify(row.get("linked_rfis") or ""),
                linked_submittals=_listify(row.get("linked_submittals") or ""),
                ref=(row.get("ref") or "").strip(),
                notes=(row.get("notes") or "").strip(),
                attachments=_listify(row.get("attachments") or ""),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return []

# ---------- metrics ----------
def _metrics(rows: List[COItem], contract_value: float) -> Dict[str, Any]:
    tot = len(rows)
    val_approved = sum(r.value_usd for r in rows if r.status == "Approved")
    val_pending  = sum(r.value_usd for r in rows if r.status in ("Proposed","Pending Client"))
    val_rejected = sum(r.value_usd for r in rows if r.status == "Rejected")
    days_net     = sum(r.days_impact for r in rows if r.status == "Approved")
    co_pct = round((val_approved / contract_value * 100.0), 2) if contract_value > 0 else 0.0
    return {
        "total": tot,
        "val_approved": val_approved,
        "val_pending": val_pending,
        "val_rejected": val_rejected,
        "days_net": days_net,
        "co_pct": co_pct
    }

# ---------- UI ----------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Change Orders")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    # Load existing
    latest = get_latest(pid, ART_TYPE, phid)
    rows: List[COItem] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [COItem(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} COs")

    state_key = _keyify("co_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    # Contract value (try get from sidebar; else input here)
    contract_value = float(st.session_state.get("capex", 0.0)) * 1_000_000.0 if st.session_state.get("capex") else 0.0
    if contract_value <= 0:
        contract_value = st.number_input("Contract value (USD)", min_value=0.0, value=0.0, step=1000.0,
                                         key=_keyify("co_contract_val", pid, phid))
    st.caption(f"Using contract value: **${contract_value:,.0f}**")

    # Import/Export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import CO CSV", type=["csv"], key=_keyify("co_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_rows(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} COs.")
        with c2:
            st.download_button(
                "Download CO CSV",
                data=_rows_to_csv(st.session_state[state_key]),
                file_name=f"{pid}_{phid}_change_orders.csv",
                mime="text/csv",
                key=_keyify("co_exp", pid, phid),
            )

    # Filters
    f1, f2, f3, f4 = st.columns([1,1,1,2])
    with f1:
        filt_status = st.multiselect("Status", STATUSES, default=[], key=_keyify("co_f_status", pid, phid))
    with f2:
        filt_reason = st.multiselect("Reason", REASONS, default=[], key=_keyify("co_f_reason", pid, phid))
    with f3:
        filt_origin = st.multiselect("Origin", ORIGINS, default=[], key=_keyify("co_f_origin", pid, phid))
    with f4:
        search = st.text_input("Search", "", key=_keyify("co_f_txt", pid, phid))

    def _pass(r: COItem) -> bool:
        if filt_status and r.status not in filt_status: return False
        if filt_reason and r.reason not in filt_reason: return False
        if filt_origin and r.origin not in filt_origin: return False
        if search:
            s = search.lower()
            blob = " ".join([
                r.id, r.title, r.origin, r.reason, r.status, r.submitted_by,
                r.owner_decision_by, r.ref, r.notes,
                ", ".join(r.linked_rfis or []), ", ".join(r.linked_submittals or []),
            ]).lower()
            if s not in blob: return False
        return True

    # KPIs
    kpi = _metrics(st.session_state[state_key], contract_value)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("Total COs", kpi["total"])
    with k2: st.metric("Approved $", f"{kpi['val_approved']:,.0f}")
    with k3: st.metric("Pending $", f"{kpi['val_pending']:,.0f}")
    with k4: st.metric("Rejected $", f"{kpi['val_rejected']:,.0f}")
    with k5: st.metric("CO % of Contract", f"{kpi['co_pct']}%")

    st.divider()

    # Add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add CO", key=_keyify("co_add", pid, phid)):
            next_num = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(COItem(id=f"CO-{next_num:03d}"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("co_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor (filtered view)
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass(r): 
            continue
        with st.expander(f"{r.id} · {r.title or 'Change Order'} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("CO ID", r.id, key=_keyify("co_id", pid, phid, idx))
                r.title = st.text_input("Title", r.title, key=_keyify("co_title", pid, phid, idx))
                r.origin = st.selectbox("Origin", ORIGINS, index=max(0, ORIGINS.index(r.origin) if r.origin in ORIGINS else 0),
                                        key=_keyify("co_origin", pid, phid, idx))
                r.reason = st.selectbox("Reason", REASONS, index=max(0, REASONS.index(r.reason) if r.reason in REASONS else 0),
                                        key=_keyify("co_reason", pid, phid, idx))
            with c2:
                r.status = st.selectbox("Status", STATUSES, index=max(0, STATUSES.index(r.status) if r.status in STATUSES else 0),
                                        key=_keyify("co_status", pid, phid, idx))
                r.submitted_by = st.text_input("Submitted by", r.submitted_by, key=_keyify("co_submit", pid, phid, idx))
                r.owner_decision_by = st.text_input("Owner decision by", r.owner_decision_by, key=_keyify("co_owner", pid, phid, idx))
            with c3:
                r.date_submitted = st.text_input("Date submitted (YYYY-MM-DD)", r.date_submitted, key=_keyify("co_dsub", pid, phid, idx))
                r.date_decided   = st.text_input("Date decided (YYYY-MM-DD)", r.date_decided, key=_keyify("co_ddcs", pid, phid, idx))
                r.ref = st.text_input("CO Ref #", r.ref, key=_keyify("co_ref", pid, phid, idx))

            c4, c5 = st.columns([1,1])
            with c4:
                r.value_usd = _parse_float(st.text_input("Value (USD)", f"{r.value_usd}", key=_keyify("co_val", pid, phid, idx)))
            with c5:
                r.days_impact = _parse_int(st.text_input("Schedule impact (days)", f"{r.days_impact}", key=_keyify("co_days", pid, phid, idx)))

            link_rfi_raw  = st.text_input("Linked RFIs (comma/newline)", ", ".join(r.linked_rfis or []), key=_keyify("co_lrfi", pid, phid, idx))
            r.linked_rfis = _listify(link_rfi_raw)
            link_sub_raw  = st.text_input("Linked Submittals (comma/newline)", ", ".join(r.linked_submittals or []), key=_keyify("co_lsub", pid, phid, idx))
            r.linked_submittals = _listify(link_sub_raw)

            r.notes = st.text_area("Notes", r.notes, key=_keyify("co_notes", pid, phid, idx))
            attach_raw = st.text_area("Attachments (links/names, comma/newline)", ", ".join(r.attachments or []), key=_keyify("co_att", pid, phid, idx))
            r.attachments = _listify(attach_raw)

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save as Draft", key=_keyify("co_save_draft", pid, phid)):
            save_artifact(pid, phid, "Commercial", ART_TYPE, payload, status="Draft")
            st.success("Change_Order_Log saved (Draft).")
    with right:
        if st.button("Save as Pending", key=_keyify("co_save_pend", pid, phid)):
            save_artifact(pid, phid, "Commercial", ART_TYPE, payload, status="Pending")
            st.success("Change_Order_Log saved (Pending).")
