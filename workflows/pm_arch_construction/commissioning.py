# workflows/pm_arch_construction/commissioning.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_SYS   = "Cx_Systems"
ART_PFC   = "PreFunc_Checks"
ART_FUNC  = "Func_Tests"
ART_DEF   = "Defect_Log"

DISCIPLINES = ["HVAC", "Electrical", "Plumbing", "Fire", "IT/ELV", "Process", "Other"]
SYS_STATUS  = ["Planned", "In-Progress", "Pre-Functional", "Functional", "Commissioned"]
RESULTS     = ["Pending", "Pass", "Fail", "N/A"]
DEF_SEV     = ["Low", "Medium", "High"]
DEF_STAT    = ["Open", "In Progress", "Closed"]

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

# ---------------- dataclasses ----------------
@dataclass
class SystemRow:
    id: str
    system: str
    area: str = ""
    discipline: str = "HVAC"
    owner: str = ""
    status: str = "Planned"      # SYS_STATUS
    turnover_package: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self); d["status"] = self.status
        return d

@dataclass
class PreFuncRow:
    id: str
    system_id: str
    checklist_item: str
    result: str = "Pending"      # RESULTS
    inspector: str = ""
    date_checked: str = ""       # YYYY-MM-DD
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self); d["date_checked"] = _safe_date_str(self.date_checked)
        return d

@dataclass
class FuncTestRow:
    id: str
    system_id: str
    test_name: str
    procedure_ref: str = ""
    result: str = "Pending"      # RESULTS
    witnessed_by: str = ""
    date_tested: str = ""        # YYYY-MM-DD
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self); d["date_tested"] = _safe_date_str(self.date_tested)
        return d

@dataclass
class DefectRow:
    id: str
    system_id: str
    location: str = ""
    description: str = ""
    severity: str = "Medium"     # DEF_SEV
    status: str = "Open"         # DEF_STAT
    due: str = ""                # YYYY-MM-DD
    owner: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self); d["due"] = _safe_date_str(self.due)
        return d

# ---------------- seeds ----------------
SEED_SYSTEMS: List[SystemRow] = [
    SystemRow(id="SYS-HVAC-01", system="AHU-1",   area="Level 1 Mechanical", discipline="HVAC"),
    SystemRow(id="SYS-HVAC-02", system="Chiller-1", area="Chiller Yard",     discipline="HVAC"),
    SystemRow(id="SYS-EL-01",   system="Main Switchboard MSB", area="Elec. Room L1", discipline="Electrical"),
    SystemRow(id="SYS-PL-01",   system="Domestic Water Pump Set", area="Pump Room",  discipline="Plumbing"),
    SystemRow(id="SYS-FS-01",   system="Fire Pump Set", area="Pump Room",    discipline="Fire"),
]

# ---------------- csv io ----------------
SYS_FIELDS  = ["id","system","area","discipline","owner","status","turnover_package","notes"]
PFC_FIELDS  = ["id","system_id","checklist_item","result","inspector","date_checked","notes"]
FUNC_FIELDS = ["id","system_id","test_name","procedure_ref","result","witnessed_by","date_tested","notes"]
DEF_FIELDS  = ["id","system_id","location","description","severity","status","due","owner","notes"]

def _rows_to_csv(fields: List[str], rows: List[Dict[str, Any]]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return sio.getvalue().encode("utf-8")

def _csv_to_systems(uploaded) -> List[SystemRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[SystemRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(SystemRow(
                id=(row.get("id") or f"SYS-{i:03d}").strip(),
                system=(row.get("system") or "").strip(),
                area=(row.get("area") or "").strip(),
                discipline=(row.get("discipline") or "HVAC").strip(),
                owner=(row.get("owner") or "").strip(),
                status=(row.get("status") or "Planned").strip(),
                turnover_package=(row.get("turnover_package") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Systems): {e}")
        return []

def _csv_to_pfc(uploaded) -> List[PreFuncRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[PreFuncRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(PreFuncRow(
                id=(row.get("id") or f"PFC-{i:03d}").strip(),
                system_id=(row.get("system_id") or "").strip(),
                checklist_item=(row.get("checklist_item") or "").strip(),
                result=(row.get("result") or "Pending").strip(),
                inspector=(row.get("inspector") or "").strip(),
                date_checked=_safe_date_str(row.get("date_checked")),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Pre-Functional): {e}")
        return []

def _csv_to_func(uploaded) -> List[FuncTestRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[FuncTestRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(FuncTestRow(
                id=(row.get("id") or f"FCT-{i:03d}").strip(),
                system_id=(row.get("system_id") or "").strip(),
                test_name=(row.get("test_name") or "").strip(),
                procedure_ref=(row.get("procedure_ref") or "").strip(),
                result=(row.get("result") or "Pending").strip(),
                witnessed_by=(row.get("witnessed_by") or "").strip(),
                date_tested=_safe_date_str(row.get("date_tested")),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Functional): {e}")
        return []

def _csv_to_def(uploaded) -> List[DefectRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[DefectRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(DefectRow(
                id=(row.get("id") or f"DEF-{i:03d}").strip(),
                system_id=(row.get("system_id") or "").strip(),
                location=(row.get("location") or "").strip(),
                description=(row.get("description") or "").strip(),
                severity=(row.get("severity") or "Medium").strip(),
                status=(row.get("status") or "Open").strip(),
                due=_safe_date_str(row.get("due")),
                owner=(row.get("owner") or "").strip(),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Defects): {e}")
        return []

# ---------------- metrics ----------------
def _commissioning_progress(systems: List[SystemRow]) -> float:
    if not systems: return 0.0
    commissioned = sum(1 for s in systems if s.status == "Commissioned")
    return round(commissioned * 100.0 / len(systems), 1)

def _result_pass_pct(rows: List[Dict[str, Any]], field: str) -> float:
    if not rows: return 0.0
    valid = [r for r in rows if r.get(field) in ("Pass","Fail","N/A","Pending")]
    if not valid: return 0.0
    passes = sum(1 for r in valid if r.get(field) == "Pass")
    return round(passes * 100.0 / len(valid), 1)

def _defect_counts(defs: List[DefectRow]) -> Dict[str, int]:
    return {
        "open": sum(1 for d in defs if d.status != "Closed"),
        "closed": sum(1 for d in defs if d.status == "Closed"),
        "high": sum(1 for d in defs if d.severity == "High" and d.status != "Closed"),
    }

# ---------------- tabs ----------------
def _systems_tab(pid: str, phid: str):
    st.caption("Define & track systems to be commissioned.")
    latest = get_latest(pid, ART_SYS, phid)
    rows: List[SystemRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [SystemRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} systems")

    state_key = _keyify("cx_sys_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows or list(SEED_SYSTEMS)

    with st.expander("📄 Import / Export / Seed", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Seed common systems", key=_keyify("cx_sys_seed", pid, phid)):
                st.session_state[state_key].extend(SEED_SYSTEMS)
                st.success(f"Seeded {len(SEED_SYSTEMS)} systems.")
        with c2:
            up = st.file_uploader("Import Systems CSV", type=["csv"], key=_keyify("cx_sys_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_systems(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} systems.")
        with c3:
            st.download_button(
                "Download Systems CSV",
                data=_rows_to_csv(SYS_FIELDS, [s.to_dict() for s in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_cx_systems.csv",
                mime="text/csv",
                key=_keyify("cx_sys_exp", pid, phid),
            )

    # Filters
    f1, f2, f3 = st.columns([1,1,2])
    with f1:
        f_disc = st.multiselect("Discipline", DISCIPLINES, default=[], key=_keyify("cx_sys_fdisc", pid, phid))
    with f2:
        f_stat = st.multiselect("Status", SYS_STATUS, default=[], key=_keyify("cx_sys_fstat", pid, phid))
    with f3:
        search = st.text_input("Search", "", key=_keyify("cx_sys_ftext", pid, phid))

    def _pass(s: SystemRow) -> bool:
        if f_disc and s.discipline not in f_disc: return False
        if f_stat and s.status not in f_stat: return False
        if search:
            stext = " ".join([s.id, s.system, s.area, s.discipline, s.owner, s.turnover_package, s.notes]).lower()
            if search.lower() not in stext: return False
        return True

    # Quick add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add system", key=_keyify("cx_sys_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(SystemRow(id=f"SYS-{n:03d}", system="New System"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("cx_sys_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, r in enumerate(st.session_state[state_key]):
        if not _pass(r): continue
        with st.expander(f"{r.id} · {r.system} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("System ID", r.id, key=_keyify("cx_sys_id", pid, phid, idx))
                r.system = st.text_input("System name", r.system, key=_keyify("cx_sys_name", pid, phid, idx))
                r.area = st.text_input("Area/Location", r.area, key=_keyify("cx_sys_area", pid, phid, idx))
            with c2:
                r.discipline = st.selectbox("Discipline", DISCIPLINES,
                                            index=max(0, DISCIPLINES.index(r.discipline) if r.discipline in DISCIPLINES else 0),
                                            key=_keyify("cx_sys_disc", pid, phid, idx))
                r.status = st.selectbox("Status", SYS_STATUS,
                                        index=max(0, SYS_STATUS.index(r.status) if r.status in SYS_STATUS else 0),
                                        key=_keyify("cx_sys_status", pid, phid, idx))
                r.owner = st.text_input("Owner", r.owner, key=_keyify("cx_sys_owner", pid, phid, idx))
            with c3:
                r.turnover_package = st.text_input("Turnover package", r.turnover_package, key=_keyify("cx_sys_pack", pid, phid, idx))
                r.notes = st.text_area("Notes", r.notes, key=_keyify("cx_sys_notes", pid, phid, idx))

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [s.to_dict() for s in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save Systems (Draft)", key=_keyify("cx_sys_save_d", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_SYS, payload, status="Draft")
            st.success("Cx_Systems saved (Draft).")
    with right:
        if st.button("Save Systems (Pending)", key=_keyify("cx_sys_save_p", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_SYS, payload, status="Pending")
            st.success("Cx_Systems saved (Pending).")

def _pfc_tab(pid: str, phid: str):
    st.caption("Pre-Functional checklists")
    latest = get_latest(pid, ART_PFC, phid)
    rows: List[PreFuncRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [PreFuncRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} checks")

    state_key = _keyify("cx_pfc_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import PFC CSV", type=["csv"], key=_keyify("cx_pfc_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_pfc(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} PFC rows.")
        with c2:
            st.download_button(
                "Download PFC CSV",
                data=_rows_to_csv(PFC_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_prefunc_checks.csv",
                mime="text/csv",
                key=_keyify("cx_pfc_exp", pid, phid),
            )

    # Quick add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add PFC row", key=_keyify("cx_pfc_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(PreFuncRow(id=f"PFC-{n:03d}", system_id="", checklist_item=""))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("cx_pfc_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, r in enumerate(st.session_state[state_key]):
        with st.expander(f"{r.id} · {r.system_id or 'System'} · {r.result}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("Row ID", r.id, key=_keyify("cx_pfc_id", pid, phid, idx))
                r.system_id = st.text_input("System ID", r.system_id, key=_keyify("cx_pfc_sys", pid, phid, idx))
                r.checklist_item = st.text_input("Checklist item", r.checklist_item, key=_keyify("cx_pfc_item", pid, phid, idx))
            with c2:
                r.result = st.selectbox("Result", RESULTS,
                                        index=max(0, RESULTS.index(r.result) if r.result in RESULTS else 0),
                                        key=_keyify("cx_pfc_res", pid, phid, idx))
                r.inspector = st.text_input("Inspector", r.inspector, key=_keyify("cx_pfc_insp", pid, phid, idx))
            with c3:
                r.date_checked = st.text_input("Date (YYYY-MM-DD)", r.date_checked, key=_keyify("cx_pfc_date", pid, phid, idx))
                r.notes = st.text_area("Notes", r.notes, key=_keyify("cx_pfc_notes", pid, phid, idx))

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save Pre-Functional (Draft)", key=_keyify("cx_pfc_save_d", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_PFC, payload, status="Draft")
            st.success("PreFunc_Checks saved (Draft).")
    with right:
        if st.button("Save Pre-Functional (Pending)", key=_keyify("cx_pfc_save_p", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_PFC, payload, status="Pending")
            st.success("PreFunc_Checks saved (Pending).")

def _func_tab(pid: str, phid: str):
    st.caption("Functional tests & witnessing")
    latest = get_latest(pid, ART_FUNC, phid)
    rows: List[FuncTestRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [FuncTestRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} tests")

    state_key = _keyify("cx_func_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import Functional CSV", type=["csv"], key=_keyify("cx_func_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_func(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} tests.")
        with c2:
            st.download_button(
                "Download Functional CSV",
                data=_rows_to_csv(FUNC_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_functional_tests.csv",
                mime="text/csv",
                key=_keyify("cx_func_exp", pid, phid),
            )

    # Quick add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add test", key=_keyify("cx_func_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(FuncTestRow(id=f"FCT-{n:03d}", system_id="", test_name=""))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("cx_func_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, r in enumerate(st.session_state[state_key]):
        with st.expander(f"{r.id} · {r.system_id or 'System'} · {r.test_name or 'Test'} · {r.result}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("Row ID", r.id, key=_keyify("cx_func_id", pid, phid, idx))
                r.system_id = st.text_input("System ID", r.system_id, key=_keyify("cx_func_sys", pid, phid, idx))
                r.test_name = st.text_input("Test name", r.test_name, key=_keyify("cx_func_name", pid, phid, idx))
            with c2:
                r.result = st.selectbox("Result", RESULTS,
                                        index=max(0, RESULTS.index(r.result) if r.result in RESULTS else 0),
                                        key=_keyify("cx_func_res", pid, phid, idx))
                r.witnessed_by = st.text_input("Witnessed by", r.witnessed_by, key=_keyify("cx_func_wit", pid, phid, idx))
            with c3:
                r.procedure_ref = st.text_input("Procedure ref", r.procedure_ref, key=_keyify("cx_func_ref", pid, phid, idx))
                r.date_tested = st.text_input("Date tested (YYYY-MM-DD)", r.date_tested, key=_keyify("cx_func_date", pid, phid, idx))
            r.notes = st.text_area("Notes", r.notes, key=_keyify("cx_func_notes", pid, phid, idx))

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save Functional (Draft)", key=_keyify("cx_func_save_d", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_FUNC, payload, status="Draft")
            st.success("Func_Tests saved (Draft).")
    with right:
        if st.button("Save Functional (Pending)", key=_keyify("cx_func_save_p", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_FUNC, payload, status="Pending")
            st.success("Func_Tests saved (Pending).")

def _defects_tab(pid: str, phid: str):
    st.caption("Defects & punch items during commissioning")
    latest = get_latest(pid, ART_DEF, phid)
    rows: List[DefectRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [DefectRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} defects")

    state_key = _keyify("cx_def_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows

    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import Defects CSV", type=["csv"], key=_keyify("cx_def_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_def(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} defects.")
        with c2:
            st.download_button(
                "Download Defects CSV",
                data=_rows_to_csv(DEF_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_defects.csv",
                mime="text/csv",
                key=_keyify("cx_def_exp", pid, phid),
            )

    # Quick add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add defect", key=_keyify("cx_def_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(DefectRow(id=f"DEF-{n:03d}", system_id="", description=""))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("cx_def_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, r in enumerate(st.session_state[state_key]):
        with st.expander(f"{r.id} · {r.system_id or 'System'} · {r.severity} · {r.status}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("Row ID", r.id, key=_keyify("cx_def_id", pid, phid, idx))
                r.system_id = st.text_input("System ID", r.system_id, key=_keyify("cx_def_sys", pid, phid, idx))
                r.location = st.text_input("Location", r.location, key=_keyify("cx_def_loc", pid, phid, idx))
            with c2:
                r.severity = st.selectbox("Severity", DEF_SEV,
                                          index=max(0, DEF_SEV.index(r.severity) if r.severity in DEF_SEV else 1),
                                          key=_keyify("cx_def_sev", pid, phid, idx))
                r.status = st.selectbox("Status", DEF_STAT,
                                        index=max(0, DEF_STAT.index(r.status) if r.status in DEF_STAT else 0),
                                        key=_keyify("cx_def_stat", pid, phid, idx))
                r.owner = st.text_input("Owner", r.owner, key=_keyify("cx_def_owner", pid, phid, idx))
            with c3:
                r.due = st.text_input("Due (YYYY-MM-DD)", r.due, key=_keyify("cx_def_due", pid, phid, idx))
            r.description = st.text_area("Description", r.description, key=_keyify("cx_def_desc", pid, phid, idx))
            r.notes = st.text_area("Notes", r.notes, key=_keyify("cx_def_notes", pid, phid, idx))

    st.divider()

    # Save
    left, right = st.columns(2)
    payload = {"rows": [r.to_dict() for r in st.session_state[state_key]], "saved_at": datetime.utcnow().isoformat() + "Z"}
    with left:
        if st.button("Save Defects (Draft)", key=_keyify("cx_def_save_d", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_DEF, payload, status="Draft")
            st.success("Defect_Log saved (Draft).")
    with right:
        if st.button("Save Defects (Pending)", key=_keyify("cx_def_save_p", pid, phid)):
            save_artifact(pid, phid, "Commissioning", ART_DEF, payload, status="Pending")
            st.success("Defect_Log saved (Pending).")

# ---------------- summary ----------------
def _summary_tab(pid: str, phid: str):
    st.caption("Commissioning summary & KPIs")

    sys_latest  = get_latest(pid, ART_SYS,  phid)
    pfc_latest  = get_latest(pid, ART_PFC,  phid)
    func_latest = get_latest(pid, ART_FUNC, phid)
    def_latest  = get_latest(pid, ART_DEF,  phid)

    systems = [SystemRow(**r) for r in (sys_latest or {}).get("data", {}).get("rows", [])] if sys_latest else []
    pfc_rows = list((pfc_latest or {}).get("data", {}).get("rows", []))
    func_rows= list((func_latest or {}).get("data", {}).get("rows", []))
    defects  = [DefectRow(**r) for r in (def_latest or {}).get("data", {}).get("rows", [])] if def_latest else []

    st.metric("Systems Commissioned %", f"{_commissioning_progress(systems)}%")
    st.metric("Pre-Functional Pass %", f"{_result_pass_pct(pfc_rows, 'result')}%")
    st.metric("Functional Pass %", f"{_result_pass_pct(func_rows, 'result')}%")
    d = _defect_counts(defects)
    st.metric("Open Defects", d["open"])
    st.metric("High Severity (Open)", d["high"])

    st.write("—")
    st.caption("Tip: Commissioning % is based on Systems marked **Commissioned** in the Systems tab.")

# ---------------- main entry ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Commissioning Tracker")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    t1, t2, t3, t4, t5 = st.tabs(["Systems", "Pre-Functional", "Functional", "Defects", "Summary"])
    with t1:
        _systems_tab(pid, phid)
    with t2:
        _pfc_tab(pid, phid)
    with t3:
        _func_tab(pid, phid)
    with t4:
        _defects_tab(pid, phid)
    with t5:
        _summary_tab(pid, phid)
