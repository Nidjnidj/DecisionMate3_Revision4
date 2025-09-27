# workflows/pm_arch_construction/cost_library.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_TYPE   = "Unit_Rate_Library"
WORKSTREAM = "Finance"
CURRENCY   = "$"

# ---------------- utils ----------------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

def _parse_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(str(x).replace(",", "").replace(CURRENCY, "").strip())
    except Exception:
        return default

def _parse_int(x: Any, default: int = 0) -> int:
    try:
        return int(float(str(x).strip()))
    except Exception:
        return default

# ---------------- dataclasses ----------------
TRADES = ["Civil", "Architectural", "Structural", "Mechanical", "Electrical", "Plumbing", "Fire", "IT/ELV", "Other"]

@dataclass
class RateItem:
    id: str
    trade: str = "Other"
    description: str = ""
    unit: str = ""             # m3, m2, m, ea, t, kg, hr, etc.
    base_rate: float = 0.0     # numeric, in currency per unit
    currency: str = CURRENCY
    base_year: int = 2025
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trade": self.trade,
            "description": self.description,
            "unit": self.unit,
            "base_rate": float(self.base_rate or 0.0),
            "currency": self.currency or CURRENCY,
            "base_year": int(self.base_year or 0),
            "notes": self.notes,
        }

@dataclass
class IndexItem:
    year: int
    index: float  # relative to an arbitrary base (e.g., base year = 1.00)

    def to_dict(self) -> Dict[str, Any]:
        return {"year": int(self.year), "index": float(self.index)}

@dataclass
class TradeFactor:
    trade: str
    factor: float  # location/market factor multiplier

    def to_dict(self) -> Dict[str, Any]:
        return {"trade": self.trade, "factor": float(self.factor)}

# ---------------- CSV schemas ----------------
RATE_FIELDS = ["id", "trade", "description", "unit", "base_rate", "currency", "base_year", "notes"]
IDX_FIELDS  = ["year", "index"]
FAC_FIELDS  = ["trade", "factor"]

def _csv_write(rows: List[Dict[str, Any]], fields: List[str]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return sio.getvalue().encode("utf-8")

def _csv_read_rates(file) -> List[RateItem]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[RateItem] = []
        for i, r in enumerate(rd, 1):
            out.append(RateItem(
                id=(r.get("id") or f"R-{i:04d}").strip(),
                trade=(r.get("trade") or "Other").strip(),
                description=(r.get("description") or "").strip(),
                unit=(r.get("unit") or "").strip(),
                base_rate=_parse_float(r.get("base_rate")),
                currency=(r.get("currency") or CURRENCY).strip() or CURRENCY,
                base_year=_parse_int(r.get("base_year"), 2025),
                notes=(r.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"Rates CSV parse error: {e}")
        return []

def _csv_read_indices(file) -> List[IndexItem]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[IndexItem] = []
        for r in rd:
            out.append(IndexItem(year=_parse_int(r.get("year")), index=_parse_float(r.get("index"), 1.0)))
        return out
    except Exception as e:
        st.error(f"Escalation CSV parse error: {e}")
        return []

def _csv_read_factors(file) -> List[TradeFactor]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[TradeFactor] = []
        for r in rd:
            out.append(TradeFactor(trade=(r.get("trade") or "Other").strip(), factor=_parse_float(r.get("factor"), 1.0)))
        return out
    except Exception as e:
        st.error(f"Factor CSV parse error: {e}")
        return []

# ---------------- escalation math ----------------
def _index_for(year: int, indices: List[IndexItem]) -> Optional[float]:
    for it in indices:
        if int(it.year) == int(year):
            return float(it.index)
    return None

def _escalate(base_rate: float, base_year: int, target_year: int,
              indices: List[IndexItem],
              location_factor: float = 1.0,
              trade: str = "Other",
              trade_factors: List[TradeFactor] = None,
              apply_trade_factor: bool = True) -> float:
    if base_rate is None:
        return 0.0
    bi = _index_for(base_year, indices)
    ti = _index_for(target_year, indices)
    if not (isinstance(bi, float) and isinstance(ti, float) and bi > 0):
        # graceful fallback: if we don't have both years, leave rate unchanged (still apply factors)
        result = float(base_rate)
    else:
        result = float(base_rate) * (ti / bi)
    result *= float(location_factor or 1.0)
    if apply_trade_factor and trade_factors:
        tf = next((x.factor for x in trade_factors if (x.trade or "").strip() == (trade or "").strip()), 1.0)
        result *= float(tf or 1.0)
    return result

# ---------------- main ----------------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Cost Library & Escalation")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    latest = get_latest(pid, ART_TYPE, phid)
    init_rates: List[RateItem] = []
    init_indices: List[IndexItem] = []
    init_factors: List[TradeFactor] = []
    default_loc_factor = 1.00

    if latest:
        data = latest.get("data", {}) or {}
        init_rates = [RateItem(**r) for r in data.get("rates", []) if r.get("id")]
        esc = data.get("escalation", {}) or {}
        init_indices = [IndexItem(**r) for r in esc.get("indices", []) if r.get("year") is not None]
        init_factors = [TradeFactor(**r) for r in esc.get("trade_factors", []) if r.get("trade")]
        default_loc_factor = float(esc.get("default_location_factor", 1.00) or 1.00)

    rates_key   = _keyify("costlib_rates", pid, phid)
    idx_key     = _keyify("costlib_indices", pid, phid)
    fac_key     = _keyify("costlib_factors", pid, phid)
    dlf_key     = _keyify("costlib_dlf", pid, phid)

    if rates_key not in st.session_state:
        st.session_state[rates_key] = init_rates or [
            RateItem(id="R-0001", trade="Civil", description="Excavation (bulk)", unit="m3", base_rate=12.0, base_year=2025),
            RateItem(id="R-0002", trade="Structural", description="Rebar supply & place", unit="t", base_rate=850.0, base_year=2025),
            RateItem(id="R-0003", trade="Electrical", description="Cable tray supply & install", unit="m", base_rate=8.0, base_year=2025),
        ]
    if idx_key not in st.session_state:
        st.session_state[idx_key] = init_indices or [
            IndexItem(year=2023, index=0.96),
            IndexItem(year=2024, index=0.98),
            IndexItem(year=2025, index=1.00),
            IndexItem(year=2026, index=1.03),
            IndexItem(year=2027, index=1.06),
        ]
    if fac_key not in st.session_state:
        st.session_state[fac_key] = init_factors or [
            TradeFactor(trade="Electrical", factor=1.05),
            TradeFactor(trade="Mechanical", factor=1.04),
        ]
    if dlf_key not in st.session_state:
        st.session_state[dlf_key] = default_loc_factor

    tab_rates, tab_escal, tab_preview = st.tabs(["Rates", "Escalation & Factors", "Apply / Preview"])

    # ---------------- Rates tab ----------------
    with tab_rates:
        st.markdown("#### Unit Rates")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            f_text = st.text_input("Filter text (trade/desc/unit)", key=_keyify("rl_ft", pid, phid))
        with c2:
            f_trade = st.multiselect("Trade", TRADES, default=TRADES, key=_keyify("rl_tr", pid, phid))
        with c3:
            st.caption(f"Total items: {len(st.session_state[rates_key])}")

        ie1, ie2, ie3 = st.columns(3)
        with ie1:
            up = st.file_uploader("Import Rates CSV", type=["csv"], key=_keyify("rl_imp", pid, phid))
            if up is not None:
                parsed = _csv_read_rates(up)
                if parsed:
                    st.session_state[rates_key] = parsed
                    st.success(f"Imported {len(parsed)} rates.")
        with ie2:
            st.download_button(
                "Download Rates CSV",
                data=_csv_write([x.to_dict() for x in st.session_state[rates_key]], RATE_FIELDS),
                file_name=f"{pid}_{phid}_unit_rates.csv",
                mime="text/csv",
                key=_keyify("rl_exp", pid, phid),
            )
        with ie3:
            if st.button("➕ Add rate", key=_keyify("rl_add", pid, phid)):
                n = len(st.session_state[rates_key]) + 1
                st.session_state[rates_key].append(RateItem(id=f"R-{n:04d}"))

        # list + editors
        def _visible_rate(x: RateItem) -> bool:
            if f_trade and (x.trade or "Other") not in f_trade: return False
            txt = (f_text or "").lower().strip()
            if txt:
                blob = " ".join([x.id, x.trade, x.description, x.unit]).lower()
                if txt not in blob:
                    return False
            return True

        for i, it in enumerate(st.session_state[rates_key]):
            if not _visible_rate(it):
                continue
            with st.expander(f"{it.id} · {it.trade} · {it.description or it.unit}", expanded=False):
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    it.id    = st.text_input("ID", it.id, key=_keyify("rl_id", pid, phid, i))
                    it.trade = st.selectbox("Trade", TRADES,
                                            index=max(0, TRADES.index(it.trade) if it.trade in TRADES else TRADES.index("Other")),
                                            key=_keyify("rl_trd", pid, phid, i))
                    it.unit  = st.text_input("Unit", it.unit, key=_keyify("rl_unit", pid, phid, i))
                with c2:
                    it.description = st.text_input("Description", it.description, key=_keyify("rl_desc", pid, phid, i))
                    it.currency    = st.text_input("Currency", it.currency or CURRENCY, key=_keyify("rl_ccy", pid, phid, i))
                with c3:
                    it.base_rate = _parse_float(st.text_input(f"Base rate ({it.currency}/unit)", f"{it.base_rate}",
                                                              key=_keyify("rl_rate", pid, phid, i)))
                    it.base_year = _parse_int(st.text_input("Base year", f"{it.base_year}", key=_keyify("rl_by", pid, phid, i)), 2025)
                it.notes = st.text_area("Notes", it.notes, key=_keyify("rl_notes", pid, phid, i))

        st.divider()
        s1, s2, s3 = st.columns(3)
        payload = _payload(pid, phid, st.session_state[rates_key], st.session_state[idx_key],
                           st.session_state[fac_key], st.session_state[dlf_key])
        with s1:
            if st.button("Save Rates (Draft)", key=_keyify("rl_save_d", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
                st.success("Rates saved (Draft).")
        with s2:
            if st.button("Save Rates (Pending)", key=_keyify("rl_save_p", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
                st.success("Rates saved (Pending).")
        with s3:
            if st.button("Save & Approve Rates", key=_keyify("rl_save_a", pid, phid)):
                rec = save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
                try:
                    from artifact_registry import approve_artifact
                    approve_artifact(pid, rec.get("artifact_id"))
                except Exception:
                    pass
                st.success("Rates saved and Approved.")

    # ---------------- Escalation & Factors tab ----------------
    with tab_escal:
        st.markdown("#### Escalation Indices & Trade Location Factors")

        st.number_input("Default location factor", min_value=0.0, step=0.01, value=float(st.session_state[dlf_key]),
                        key=_keyify("dlf_display_only", pid, phid), disabled=True)
        # Sync back to session state via text input (number_input can be disabled)
        new_dlf = st.text_input("Edit default location factor", f"{st.session_state[dlf_key]:.2f}",
                                key=_keyify("dlf_edit", pid, phid))
        try:
            st.session_state[dlf_key] = float(new_dlf)
        except Exception:
            pass

        st.caption("Escalation index is relative (e.g., 2025 = 1.00). Rate(target) = Rate(base) × (Index[target]/Index[base]) × location × trade_factor.")

        # Indices import/export
        i1, i2, i3 = st.columns(3)
        with i1:
            upi = st.file_uploader("Import Indices CSV", type=["csv"], key=_keyify("idx_imp", pid, phid))
            if upi is not None:
                parsed = _csv_read_indices(upi)
                if parsed:
                    st.session_state[idx_key] = parsed
                    st.success(f"Imported {len(parsed)} index rows.")
        with i2:
            st.download_button(
                "Download Indices CSV",
                data=_csv_write([x.to_dict() for x in st.session_state[idx_key]], IDX_FIELDS),
                file_name=f"{pid}_{phid}_indices.csv",
                mime="text/csv",
                key=_keyify("idx_exp", pid, phid),
            )
        with i3:
            if st.button("➕ Add index row", key=_keyify("idx_add", pid, phid)):
                guess_year = (max([x.year for x in st.session_state[idx_key]] + [2025]) + 1)
                st.session_state[idx_key].append(IndexItem(year=guess_year, index=1.00))

        for i, it in enumerate(sorted(st.session_state[idx_key], key=lambda x: x.year)):
            with st.expander(f"{it.year} · {it.index:.3f}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    it.year = _parse_int(st.text_input("Year", f"{it.year}", key=_keyify("idx_y", pid, phid, i)))
                with c2:
                    it.index = _parse_float(st.text_input("Index", f"{it.index}", key=_keyify("idx_i", pid, phid, i)), 1.0)

        st.divider()

        # Trade factors import/export
        f1, f2, f3 = st.columns(3)
        with f1:
            upf = st.file_uploader("Import Trade Factors CSV", type=["csv"], key=_keyify("fac_imp", pid, phid))
            if upf is not None:
                parsed = _csv_read_factors(upf)
                if parsed:
                    st.session_state[fac_key] = parsed
                    st.success(f"Imported {len(parsed)} trade factors.")
        with f2:
            st.download_button(
                "Download Trade Factors CSV",
                data=_csv_write([x.to_dict() for x in st.session_state[fac_key]], FAC_FIELDS),
                file_name=f"{pid}_{phid}_trade_factors.csv",
                mime="text/csv",
                key=_keyify("fac_exp", pid, phid),
            )
        with f3:
            if st.button("➕ Add trade factor", key=_keyify("fac_add", pid, phid)):
                st.session_state[fac_key].append(TradeFactor(trade="Electrical", factor=1.00))

        for i, tf in enumerate(st.session_state[fac_key]):
            with st.expander(f"{tf.trade} · {tf.factor:.2f}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    tf.trade = st.selectbox("Trade", TRADES,
                                            index=max(0, TRADES.index(tf.trade) if tf.trade in TRADES else TRADES.index("Other")),
                                            key=_keyify("fac_tr", pid, phid, i))
                with c2:
                    tf.factor = _parse_float(st.text_input("Factor", f"{tf.factor}", key=_keyify("fac_fc", pid, phid, i)), 1.0)

        st.divider()
        s1, s2, s3 = st.columns(3)
        payload = _payload(pid, phid, st.session_state[rates_key], st.session_state[idx_key],
                           st.session_state[fac_key], st.session_state[dlf_key])
        with s1:
            if st.button("Save Escalation (Draft)", key=_keyify("es_save_d", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
                st.success("Escalation saved (Draft).")
        with s2:
            if st.button("Save Escalation (Pending)", key=_keyify("es_save_p", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
                st.success("Escalation saved (Pending).")
        with s3:
            if st.button("Save & Approve Escalation", key=_keyify("es_save_a", pid, phid)):
                rec = save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Pending")
                try:
                    from artifact_registry import approve_artifact
                    approve_artifact(pid, rec.get("artifact_id"))
                except Exception:
                    pass
                st.success("Escalation saved and Approved.")

    # ---------------- Preview tab ----------------
    with tab_preview:
        st.markdown("#### Apply Escalation / Preview Rates")
        years = sorted({x.year for x in st.session_state[idx_key]})
        if not years:
            st.warning("Please define at least one escalation index year in the previous tab.")
            return

        c1, c2, c3, c4 = st.columns([1,1,1,1])
        with c1:
            target_year = st.selectbox("Target year", years, index=len(years)-1, key=_keyify("pv_year", pid, phid))
        with c2:
            locf = st.number_input("Location factor", min_value=0.0, step=0.01,
                                   value=float(st.session_state[dlf_key]), key=_keyify("pv_locf", pid, phid))
        with c3:
            apply_tf = st.checkbox("Apply trade factors", value=True, key=_keyify("pv_applytf", pid, phid))
        with c4:
            filt_trade = st.multiselect("Trade filter", TRADES, default=TRADES, key=_keyify("pv_tr", pid, phid))

        ftext = st.text_input("Text filter (id/desc/unit)", key=_keyify("pv_ft", pid, phid))

        # Generate preview rows
        preview_rows: List[Dict[str, Any]] = []
        for it in st.session_state[rates_key]:
            if filt_trade and it.trade not in filt_trade:
                continue
            t = (ftext or "").lower().strip()
            if t:
                blob = " ".join([it.id, it.description, it.unit]).lower()
                if t not in blob:
                    continue
            esc = _escalate(
                base_rate=it.base_rate,
                base_year=int(it.base_year),
                target_year=int(target_year),
                indices=st.session_state[idx_key],
                location_factor=locf,
                trade=it.trade,
                trade_factors=st.session_state[fac_key],
                apply_trade_factor=apply_tf,
            )
            preview_rows.append({
                "id": it.id,
                "trade": it.trade,
                "description": it.description,
                "unit": it.unit,
                "currency": it.currency or CURRENCY,
                "base_year": int(it.base_year),
                "base_rate": float(it.base_rate),
                "target_year": int(target_year),
                "escalated_rate": round(esc, 2),
                "delta": round(esc - float(it.base_rate or 0.0), 2),
            })

        st.dataframe(preview_rows, use_container_width=True)

        st.divider()
        # Save a *snapshot* as the same artifact (it’s still the library but with last preview info)
        if st.button("Save Preview Snapshot (Draft)", key=_keyify("pv_save", pid, phid)):
            payload = _payload(pid, phid, st.session_state[rates_key], st.session_state[idx_key],
                               st.session_state[fac_key], st.session_state[dlf_key])
            payload["preview"] = {
                "target_year": int(target_year),
                "location_factor": float(locf),
                "apply_trade_factors": bool(apply_tf),
                "rows": preview_rows,
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }
            save_artifact(pid, phid, WORKSTREAM, ART_TYPE, payload, status="Draft")
            st.success("Preview snapshot saved (Draft).")

# ---------------- payload builder ----------------
def _payload(pid: str, phid: str,
             rates: List[RateItem],
             indices: List[IndexItem],
             factors: List[TradeFactor],
             default_loc_factor: float) -> Dict[str, Any]:
    return {
        "project_id": pid,
        "phase_id": phid,
        "rates": [x.to_dict() for x in rates],
        "escalation": {
            "indices": [x.to_dict() for x in indices],
            "trade_factors": [x.to_dict() for x in factors],
            "default_location_factor": float(default_loc_factor or 1.0),
        },
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
