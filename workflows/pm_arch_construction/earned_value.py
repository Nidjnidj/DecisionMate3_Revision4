# workflows/pm_arch_construction/earned_value.py
from __future__ import annotations
import csv, io, re, math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, date

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_EV_SNAPSHOT  = "EV_Snapshot"
ART_EV_TIMESER   = "EV_Timeseries"

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

def _parse_float(x: Any) -> float:
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return 0.0

# ---------------- dataclasses ----------------
@dataclass
class EVRow:
    id: str
    name: str = ""
    wbs_id: str = ""
    activity_id: str = ""
    bac: float = 0.0          # Budget at Completion (for this WP)
    pct_planned: float = 0.0  # 0..100
    pct_earned: float = 0.0   # 0..100
    ac: float = 0.0           # Actual Cost to date
    notes: str = ""

    def calc(self) -> Dict[str, float]:
        pv = self.bac * (self.pct_planned/100.0)
        ev = self.bac * (self.pct_earned/100.0)
        ac = self.ac
        cv = ev - ac
        sv = ev - pv
        cpi = (ev / ac) if ac > 0 else (math.nan if ev > 0 else 1.0)
        spi = (ev / pv) if pv > 0 else (math.nan if ev > 0 else 1.0)
        # EAC formula: AC + (BAC - EV)/CPI (if CPI>0), else fallback BAC
        if cpi and not math.isnan(cpi) and cpi > 0:
            eac = ac + (self.bac - ev)/cpi
        else:
            eac = self.bac
        etc = max(0.0, eac - ac)
        # TCPI = (BAC - EV)/(BAC - AC)
        tcpi = ((self.bac - ev) / (self.bac - ac)) if (self.bac - ac) != 0 else math.nan
        return {"pv": pv, "ev": ev, "ac": ac, "cv": cv, "sv": sv, "cpi": cpi, "spi": spi, "eac": eac, "etc": etc, "tcpi": tcpi}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.update(self.calc())
        return d

@dataclass
class EVPoint:
    period: str        # YYYY-MM
    pv: float = 0.0
    ev: float = 0.0
    ac: float = 0.0
    bac: float = 0.0   # optional constant line

    def to_dict(self) -> Dict[str, Any]:
        return {"period": self.period, "pv": self.pv, "ev": self.ev, "ac": self.ac, "bac": self.bac}

# ---------------- CSV IO ----------------
EV_FIELDS = ["id","name","wbs_id","activity_id","bac","pct_planned","pct_earned","ac","notes"]
TS_FIELDS = ["period","pv","ev","ac","bac"]

def _rows_to_csv(fields: List[str], rows: List[Dict[str, Any]]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for r in rows:
        # only write requested fields
        w.writerow({k: r.get(k, "") for k in fields})
    return sio.getvalue().encode("utf-8")

def _csv_to_ev(uploaded) -> List[EVRow]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[EVRow] = []
        for i, row in enumerate(rd, start=1):
            out.append(EVRow(
                id=(row.get("id") or f"WP-{i:03d}").strip(),
                name=(row.get("name") or "").strip(),
                wbs_id=(row.get("wbs_id") or "").strip(),
                activity_id=(row.get("activity_id") or "").strip(),
                bac=_parse_float(row.get("bac")),
                pct_planned=_parse_float(row.get("pct_planned")),
                pct_earned=_parse_float(row.get("pct_earned")),
                ac=_parse_float(row.get("ac")),
                notes=(row.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (EV rows): {e}")
        return []

def _csv_to_ts(uploaded) -> List[EVPoint]:
    try:
        content = uploaded.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[EVPoint] = []
        for row in rd:
            out.append(EVPoint(
                period=(row.get("period") or "").strip(),
                pv=_parse_float(row.get("pv")),
                ev=_parse_float(row.get("ev")),
                ac=_parse_float(row.get("ac")),
                bac=_parse_float(row.get("bac")),
            ))
        return out
    except Exception as e:
        st.error(f"CSV parse error (Timeseries): {e}")
        return []

# ---------------- seeds from artifacts ----------------
def _read_bac_from_cost_model(pid: str, phid: str) -> float:
    cm = get_latest(pid, "Cost_Model", phid)
    if not cm: return 0.0
    data = cm.get("data", {}) or {}
    total = data.get("total")
    if isinstance(total, (int, float)):
        return float(total)
    # sum items if total missing
    s = 0.0
    for it in data.get("items", []):
        s += _parse_float(it.get("cost", 0))
    return s

def _seed_rows_from_wbs_schedule(pid: str, phid: str, bac_total: float, max_rows: int = 15) -> List[EVRow]:
    # Try WBS nodes
    rows: List[EVRow] = []
    wbs = get_latest(pid, "WBS", phid)
    if wbs:
        nodes = list((wbs.get("data", {}) or {}).get("nodes", []))
        # choose leaf nodes only
        leafs = [n for n in nodes if not any(m.get("parent")==n.get("id") for m in nodes)]
        leafs = [n for n in leafs if n.get("id") and n.get("name")]
        leafs = leafs[:max_rows] if max_rows>0 else leafs
        share = bac_total/len(leafs) if leafs else 0.0
        for i, n in enumerate(leafs, start=1):
            rows.append(EVRow(
                id=f"WP-{i:03d}",
                name=n.get("name",""),
                wbs_id=n.get("id",""),
                activity_id="",
                bac=round(share,2),
                pct_planned=0.0,
                pct_earned=0.0,
                ac=0.0,
            ))
        return rows

    # else try schedule activities
    sched = get_latest(pid, "Schedule_Network", phid)
    if sched:
        acts = list((sched.get("data", {}) or {}).get("activities", []))[:max_rows]
        share = bac_total/len(acts) if acts else 0.0
        for i, a in enumerate(acts, start=1):
            rows.append(EVRow(
                id=f"WP-{i:03d}",
                name=a.get("name",""),
                wbs_id=a.get("wbs_id",""),
                activity_id=a.get("id",""),
                bac=round(share,2),
            ))
    return rows

# ---------------- rollups ----------------
def _rollup(rows: List[EVRow]) -> Dict[str, float]:
    pv = ev = ac = bac = 0.0
    for r in rows:
        calc = r.calc()
        pv += calc["pv"]; ev += calc["ev"]; ac += calc["ac"]; bac += r.bac
    cv = ev - ac
    sv = ev - pv
    cpi = (ev / ac) if ac > 0 else (math.nan if ev > 0 else 1.0)
    spi = (ev / pv) if pv > 0 else (math.nan if ev > 0 else 1.0)
    if cpi and not math.isnan(cpi) and cpi > 0:
        eac = ac + (bac - ev)/cpi
    else:
        eac = bac
    etc = max(0.0, eac - ac)
    tcpi = ((bac - ev) / (bac - ac)) if (bac - ac) != 0 else math.nan
    pct_complete = round((ev / bac * 100.0), 2) if bac > 0 else 0.0
    return {
        "pv": pv, "ev": ev, "ac": ac, "cv": cv, "sv": sv,
        "cpi": cpi, "spi": spi, "eac": eac, "etc": etc,
        "tcpi": tcpi, "bac": bac, "pct_complete": pct_complete
    }

# ---------------- UI: Work Package EV ----------------
def _wp_tab(pid: str, phid: str):
    st.caption("Work Package level EV (PV/EV/AC per WP).")

    # Load latest snapshot
    latest = get_latest(pid, ART_EV_SNAPSHOT, phid)
    rows: List[EVRow] = []
    if latest:
        data = latest.get("data", {}) or {}
        rows = [EVRow(**r) for r in data.get("rows", []) if r.get("id")]
        st.caption(f"Latest saved status: **{latest.get('status','Pending')}** · {len(rows)} WP(s)")

    # Determine BAC baseline
    bac_total = _read_bac_from_cost_model(pid, phid)
    if bac_total <= 0:
        # fallback to sidebar CAPEX (M$) if present
        capex_musd = st.session_state.get("capex", 0.0)
        bac_total = float(capex_musd) * 1_000_000.0 if capex_musd else 0.0
    st.caption(f"Using BAC baseline: **${bac_total:,.0f}**")

    # Session rows
    state_key = _keyify("ev_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = rows or _seed_rows_from_wbs_schedule(pid, phid, bac_total)

    # Import/Export
    with st.expander("📄 Import / Export / Seed", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            up = st.file_uploader("Import EV CSV", type=["csv"], key=_keyify("ev_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_ev(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} work packages.")
        with c2:
            st.download_button(
                "Download EV CSV",
                data=_rows_to_csv(EV_FIELDS, [r.to_dict() for r in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_ev_rows.csv",
                mime="text/csv",
                key=_keyify("ev_exp", pid, phid),
            )
        with c3:
            if st.button("Seed from WBS/Schedule", key=_keyify("ev_seed", pid, phid)):
                st.session_state[state_key] = _seed_rows_from_wbs_schedule(pid, phid, bac_total)
                st.success(f"Seeded {len(st.session_state[state_key])} rows.")

    # Quick add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add WP", key=_keyify("ev_add", pid, phid)):
            n = len(st.session_state[state_key]) + 1
            st.session_state[state_key].append(EVRow(id=f"WP-{n:03d}"))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("ev_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, r in enumerate(st.session_state[state_key]):
        c = r.calc()
        with st.expander(f"{r.id} · {r.name or r.wbs_id or r.activity_id or 'Work Package'}", expanded=False):
            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                r.id = st.text_input("WP ID", r.id, key=_keyify("ev_id", pid, phid, idx))
                r.name = st.text_input("Name", r.name, key=_keyify("ev_name", pid, phid, idx))
                r.wbs_id = st.text_input("WBS ID", r.wbs_id, key=_keyify("ev_wbs", pid, phid, idx))
            with c2:
                r.activity_id = st.text_input("Activity ID", r.activity_id, key=_keyify("ev_act", pid, phid, idx))
                r.bac = _parse_float(st.text_input("BAC ($)", f"{r.bac}", key=_keyify("ev_bac", pid, phid, idx)))
                r.ac = _parse_float(st.text_input("AC to date ($)", f"{r.ac}", key=_keyify("ev_ac", pid, phid, idx)))
            with c3:
                r.pct_planned = _parse_float(st.text_input("Planned %", f"{r.pct_planned}", key=_keyify("ev_pp", pid, phid, idx)))
                r.pct_earned  = _parse_float(st.text_input("Earned %", f"{r.pct_earned}", key=_keyify("ev_pe", pid, phid, idx)))
            r.notes = st.text_area("Notes", r.notes, key=_keyify("ev_notes", pid, phid, idx))

            st.caption(f"PV: ${c['pv']:,.0f} · EV: ${c['ev']:,.0f} · AC: ${c['ac']:,.0f} · "
                       f"CV: ${c['cv']:,.0f} · SV: ${c['sv']:,.0f} · CPI: {0 if math.isnan(c['cpi']) else round(c['cpi'],2)} · "
                       f"SPI: {0 if math.isnan(c['spi']) else round(c['spi'],2)} · EAC: ${c['eac']:,.0f} · ETC: ${c['etc']:,.0f} · "
                       f"TCPI: {0 if math.isnan(c['tcpi']) else round(c['tcpi'],2)}")

    st.divider()

    # Roll-up metrics
    roll = _rollup(st.session_state[state_key])
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1: st.metric("BAC", f"${roll['bac']:,.0f}")
    with m2: st.metric("PV",  f"${roll['pv']:,.0f}")
    with m3: st.metric("EV",  f"${roll['ev']:,.0f}")
    with m4: st.metric("AC",  f"${roll['ac']:,.0f}")
    with m5: st.metric("CPI", 0 if math.isnan(roll["cpi"]) else round(roll["cpi"], 2))
    with m6: st.metric("SPI", 0 if math.isnan(roll["spi"]) else round(roll["spi"], 2))
    st.caption(f"CV: ${roll['cv']:,.0f} · SV: ${roll['sv']:,.0f} · EAC: ${roll['eac']:,.0f} · ETC: ${roll['etc']:,.0f} · "
               f"TCPI: {0 if math.isnan(roll['tcpi']) else round(roll['tcpi'],2)} · % Complete: {roll['pct_complete']}%")

    # Save
    payload = {
        "rows": [r.to_dict() for r in st.session_state[state_key]],
        "rollup": roll,
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    left, right = st.columns(2)
    with left:
        if st.button("Save EV Snapshot (Draft)", key=_keyify("ev_save_draft", pid, phid)):
            save_artifact(pid, phid, "Finance", ART_EV_SNAPSHOT, payload, status="Draft")
            st.success("EV_Snapshot saved (Draft).")
    with right:
        if st.button("Save EV Snapshot (Pending)", key=_keyify("ev_save_pend", pid, phid)):
            save_artifact(pid, phid, "Finance", ART_EV_SNAPSHOT, payload, status="Pending")
            st.success("EV_Snapshot saved (Pending).")

# ---------------- UI: S-curve / Periods ----------------
def _ts_tab(pid: str, phid: str):
    st.caption("Enter monthly (or weekly) PV/EV/AC to build an S-curve and save a timeseries.")

    latest = get_latest(pid, ART_EV_TIMESER, phid)
    points: List[EVPoint] = []
    if latest:
        data = latest.get("data", {}) or {}
        points = [EVPoint(**p) for p in data.get("points", []) if p.get("period")]

    state_key = _keyify("ev_ts_rows", pid, phid)
    if state_key not in st.session_state:
        st.session_state[state_key] = points

    # Import/Export
    with st.expander("📄 Import / Export", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            up = st.file_uploader("Import Timeseries CSV", type=["csv"], key=_keyify("evts_imp", pid, phid))
            if up is not None:
                parsed = _csv_to_ts(up)
                if parsed:
                    st.session_state[state_key] = parsed
                    st.success(f"Imported {len(parsed)} periods.")
        with c2:
            st.download_button(
                "Download Timeseries CSV",
                data=_rows_to_csv(TS_FIELDS, [p.to_dict() for p in st.session_state[state_key]]),
                file_name=f"{pid}_{phid}_ev_timeseries.csv",
                mime="text/csv",
                key=_keyify("evts_exp", pid, phid),
            )

    # Add/remove
    cadd, crem = st.columns([1,1])
    with cadd:
        if st.button("➕ Add period", key=_keyify("evts_add", pid, phid)):
            st.session_state[state_key].append(EVPoint(period=date.today().strftime("%Y-%m")))
    with crem:
        if st.button("🗑️ Remove last", key=_keyify("evts_del", pid, phid)):
            if st.session_state[state_key]:
                st.session_state[state_key].pop()

    # Editor
    for idx, p in enumerate(st.session_state[state_key]):
        with st.expander(f"{p.period} · PV {p.pv:,.0f} · EV {p.ev:,.0f} · AC {p.ac:,.0f}", expanded=False):
            c1, c2, c3, c4 = st.columns([1,1,1,1])
            with c1:
                p.period = st.text_input("Period (YYYY-MM)", p.period, key=_keyify("evts_per", pid, phid, idx))
            with c2:
                p.pv = _parse_float(st.text_input("PV", f"{p.pv}", key=_keyify("evts_pv", pid, phid, idx)))
            with c3:
                p.ev = _parse_float(st.text_input("EV", f"{p.ev}", key=_keyify("evts_ev", pid, phid, idx)))
            with c4:
                p.ac = _parse_float(st.text_input("AC", f"{p.ac}", key=_keyify("evts_ac", pid, phid, idx)))
        # Optional BAC line per period (use roll-up BAC for reference)
        p.bac = p.bac or 0.0

    st.divider()

    # Simple chart (Streamlit built-in)
    try:
        import pandas as pd
        if st.session_state[state_key]:
            df = pd.DataFrame([p.to_dict() for p in st.session_state[state_key]]).sort_values("period")
            df_plot = df[["period","pv","ev","ac"]].set_index("period")
            st.line_chart(df_plot)
    except Exception:
        pass

    # Save
    payload = {
        "points": [p.to_dict() for p in st.session_state[state_key]],
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    left, right = st.columns(2)
    with left:
        if st.button("Save Timeseries (Draft)", key=_keyify("evts_save_d", pid, phid)):
            save_artifact(pid, phid, "Finance", ART_EV_TIMESER, payload, status="Draft")
            st.success("EV_Timeseries saved (Draft).")
    with right:
        if st.button("Save Timeseries (Pending)", key=_keyify("evts_save_p", pid, phid)):
            save_artifact(pid, phid, "Finance", ART_EV_TIMESER, payload, status="Pending")
            st.success("EV_Timeseries saved (Pending).")

# ---------------- main entry ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Earned Value (EV)")
    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    t1, t2 = st.tabs(["Work Package EV", "S-Curve / Periods"])
    with t1:
        _wp_tab(pid, phid)
    with t2:
        _ts_tab(pid, phid)
