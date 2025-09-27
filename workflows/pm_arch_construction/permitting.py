# workflows/pm_arch_construction/permitting.py
from __future__ import annotations
import csv
import io
from dataclasses import dataclass, asdict
from datetime import date
from typing import List, Dict, Any, Optional

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE = "Permitting_Checklist"

# ---------------- Helpers ----------------
def _keyify(*parts: Any) -> str:
    import re
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

STATUSES = ["Not Required", "Pending", "Submitted", "Approved", "Rejected"]

@dataclass
class PermitRow:
    name: str
    required: bool = True
    status: str = "Pending"
    responsible: str = ""
    due: Optional[str] = ""
    ref_no: str = ""
    link: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# sensible defaults by project flavor
DEFAULTS: Dict[str, List[PermitRow]] = {
    "Building / Civil": [
        PermitRow("Zoning clearance"),
        PermitRow("Planning approval"),
        PermitRow("Environmental impact (EIA)", required=False),
        PermitRow("Building permit"),
        PermitRow("Fire authority NOC"),
        PermitRow("Utilities connection", status="Not Required"),
        PermitRow("Occupancy certificate", status="Not Required"),
    ],
    "Industrial": [
        PermitRow("Land use / zoning"),
        PermitRow("Environmental permit (air/water)"),
        PermitRow("Hazardous materials registration", required=False),
        PermitRow("Construction permit"),
        PermitRow("Electrical substation approval"),
        PermitRow("Boiler/pressure vessel certificate", required=False),
        PermitRow("Commissioning & operation license", status="Not Required"),
    ],
    "Healthcare": [
        PermitRow("Health authority concept approval"),
        PermitRow("Medical gas compliance"),
        PermitRow("Radiation safety (if applicable)", required=False),
        PermitRow("Building permit"),
        PermitRow("Fire authority NOC"),
        PermitRow("Occupancy/operation license", status="Not Required"),
    ],
    "Education": [
        PermitRow("Education authority approval"),
        PermitRow("Planning approval"),
        PermitRow("Environmental screening", required=False),
        PermitRow("Building permit"),
        PermitRow("Fire authority NOC"),
        PermitRow("Utilities connection", status="Not Required"),
        PermitRow("Occupancy certificate", status="Not Required"),
    ],
}

def _init_state(key: str, value):
    if key not in st.session_state:
        st.session_state[key] = value
    return st.session_state[key]

def _percent_approved(rows: List[PermitRow]) -> float:
    if not rows:
        return 0.0
    # count only required (or explicitly set to required==True) for progress
    req = [r for r in rows if r.required]
    if not req:
        return 0.0
    done = sum(1 for r in req if r.status == "Approved")
    return round(done * 100.0 / len(req), 1)

def _download_csv(rows: List[PermitRow]) -> bytes:
    f = io.StringIO()
    writer = csv.DictWriter(
        f,
        fieldnames=["name", "required", "status", "responsible", "due", "ref_no", "link", "notes"],
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r.to_dict())
    return f.getvalue().encode("utf-8")

def _parse_csv(uploaded) -> List[PermitRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(content))
        rows: List[PermitRow] = []
        for row in reader:
            rows.append(
                PermitRow(
                    name=row.get("name", "").strip(),
                    required=str(row.get("required", "True")).strip().lower() in ("1", "true", "yes", "y"),
                    status=(row.get("status", "Pending").strip() or "Pending"),
                    responsible=row.get("responsible", "").strip(),
                    due=row.get("due", "").strip(),
                    ref_no=row.get("ref_no", "").strip(),
                    link=row.get("link", "").strip(),
                    notes=row.get("notes", "").strip(),
                )
            )
        return rows
    except Exception as e:
        st.error(f"CSV parse error: {e}")
        return []

# ---------------- Main entry ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Permitting & Zoning Checklist")
    pid = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id or st.session_state.get("current_phase_id", "PH-FEL1")

    # Pick a template (non-destructive; you can import/override later)
    kind = st.selectbox(
        "Template",
        list(DEFAULTS.keys()),
        index=0,
        key=_keyify("perm_template", pid, phid),
    )

    # Load latest saved (if any)
    latest = get_latest(pid, ART_TYPE, phid)
    if latest:
        data = latest.get("data", {}) or {}
        rows_raw = data.get("rows", [])
        rows: List[PermitRow] = [PermitRow(**r) for r in rows_raw if r.get("name")]
        current_status = latest.get("status", "Pending")
        st.caption(f"Latest saved status: **{current_status}**")
    else:
        rows = [PermitRow(**r.to_dict()) for r in DEFAULTS[kind]]

    # Keep rows in session while editing
    rows = _init_state(_keyify("perm_rows", pid, phid), rows)

    # CSV import/export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader(
                "Import CSV (columns: name,required,status,responsible,due,ref_no,link,notes)",
                type=["csv"],
                key=_keyify("perm_upload", pid, phid),
            )
            if up is not None:
                parsed = _parse_csv(up)
                if parsed:
                    st.session_state[_keyify("perm_rows", pid, phid)] = parsed
                    st.success(f"Imported {len(parsed)} rows.")
        with c2:
            data_bytes = _download_csv(st.session_state[_keyify("perm_rows", pid, phid)])
            st.download_button(
                "Download CSV",
                data=data_bytes,
                file_name=f"{pid}_{phid}_permitting.csv",
                mime="text/csv",
                key=_keyify("perm_export", pid, phid),
            )

    st.divider()

    # Editor
    st.caption("Edit the permitting checklist below. Use Add/Remove to manage rows.")
    add_col, del_col, ok_col = st.columns([1, 1, 2])
    with add_col:
        if st.button("➕ Add row", key=_keyify("perm_add", pid, phid)):
            st.session_state[_keyify("perm_rows", pid, phid)].append(PermitRow("New permit"))
    with del_col:
        if st.button("🗑️ Remove last", key=_keyify("perm_remove", pid, phid)):
            if st.session_state[_keyify("perm_rows", pid, phid)]:
                st.session_state[_keyify("perm_rows", pid, phid)].pop()
    with ok_col:
        if st.button("Mark all required as Approved", key=_keyify("perm_mark_all", pid, phid)):
            for r in st.session_state[_keyify("perm_rows", pid, phid)]:
                if r.required:
                    r.status = "Approved"

    # Render each row in an expander
    for idx, r in enumerate(st.session_state[_keyify("perm_rows", pid, phid)]):
        with st.expander(f"{idx+1}. {r.name or 'Permit'}", expanded=False):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                r.name = st.text_input("Permit name", value=r.name, key=_keyify("name", pid, phid, idx))
                r.responsible = st.text_input("Responsible", value=r.responsible, key=_keyify("resp", pid, phid, idx))
                r.notes = st.text_area("Notes", value=r.notes, key=_keyify("notes", pid, phid, idx))
            with c2:
                r.required = st.checkbox("Required", value=r.required, key=_keyify("req", pid, phid, idx))
                r.status = st.selectbox("Status", STATUSES, index=max(0, STATUSES.index(r.status) if r.status in STATUSES else 1),
                                        key=_keyify("status", pid, phid, idx))
                r.ref_no = st.text_input("Reference #", value=r.ref_no, key=_keyify("ref", pid, phid, idx))
            with c3:
                due_val = r.due or ""
                r.due = st.text_input("Due date (YYYY-MM-DD)", value=due_val, key=_keyify("due", pid, phid, idx))
                r.link = st.text_input("Doc/link", value=r.link, key=_keyify("link", pid, phid, idx))

    st.divider()

    # Progress
    pct = _percent_approved(st.session_state[_keyify("perm_rows", pid, phid)])
    st.metric("Required permits approved", f"{pct:.1f}%")

    # Save buttons
    left, right = st.columns(2)
    payload = {
        "template": kind,
        "rows": [r.to_dict() for r in st.session_state[_keyify("perm_rows", pid, phid)]],
    }

    with left:
        if st.button("Save as Draft"):
            save_artifact(pid, phid, "Compliance", ART_TYPE, payload, status="Draft")
            st.success("Permitting checklist saved (Draft).")
    with right:
        if st.button("Save as Pending"):
            save_artifact(pid, phid, "Compliance", ART_TYPE, payload, status="Pending")
            st.success("Permitting checklist saved (Pending).")
