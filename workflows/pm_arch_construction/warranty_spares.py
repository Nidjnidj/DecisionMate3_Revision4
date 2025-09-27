# workflows/pm_arch_construction/warranty_spares.py
from __future__ import annotations
import csv, io, re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import date, datetime

import streamlit as st
from artifact_registry import save_artifact, get_latest

ART_WARRANTIES = "Warranties"
ART_SPARES     = "Spares_List"
WORKSTREAM     = "Handover"   # change to "Maintenance" if you prefer

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


# ---------- dataclasses ----------
@dataclass
class WarrantyItem:
    id: str
    asset: str = ""           # equipment/room/system
    vendor: str = ""
    serial: str = ""
    start_date: str = ""      # YYYY-MM-DD
    end_date: str = ""        # YYYY-MM-DD
    terms: str = ""           # coverage summary
    contact: str = ""         # contact info
    attachments: List[str] = None  # links/filenames
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset": self.asset,
            "vendor": self.vendor,
            "serial": self.serial,
            "start_date": _safe_date(self.start_date),
            "end_date": _safe_date(self.end_date),
            "terms": self.terms,
            "contact": self.contact,
            "attachments": list(self.attachments or []),
            "notes": self.notes,
        }

@dataclass
class SpareItem:
    id: str
    part_no: str = ""
    description: str = ""
    vendor: str = ""
    location: str = ""        # store/room/bin
    quantity: int = 0
    min_qty: int = 0
    lead_time_days: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "part_no": self.part_no,
            "description": self.description,
            "vendor": self.vendor,
            "location": self.location,
            "quantity": int(self.quantity or 0),
            "min_qty": int(self.min_qty or 0),
            "lead_time_days": int(self.lead_time_days or 0),
            "notes": self.notes,
        }


# ---------- CSV I/O ----------
W_FIELDS = ["id","asset","vendor","serial","start_date","end_date","terms","contact","attachments","notes"]
S_FIELDS = ["id","part_no","description","vendor","location","quantity","min_qty","lead_time_days","notes"]

def _csv_write(rows: List[Dict[str, Any]], fields: List[str]) -> bytes:
    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for r in rows:
        row = dict(r)
        if "attachments" in row and isinstance(row["attachments"], list):
            row["attachments"] = "; ".join(row["attachments"])
        w.writerow({k: row.get(k, "") for k in fields})
    return sio.getvalue().encode("utf-8")

def _csv_read_warranties(file) -> List[WarrantyItem]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[WarrantyItem] = []
        for i, r in enumerate(rd, 1):
            out.append(WarrantyItem(
                id=(r.get("id") or f"W-{i:04d}").strip(),
                asset=(r.get("asset") or "").strip(),
                vendor=(r.get("vendor") or "").strip(),
                serial=(r.get("serial") or "").strip(),
                start_date=_safe_date(r.get("start_date")),
                end_date=_safe_date(r.get("end_date")),
                terms=(r.get("terms") or "").strip(),
                contact=(r.get("contact") or "").strip(),
                attachments=_listify(r.get("attachments") or ""),
                notes=(r.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"Warranties CSV parse error: {e}")
        return []

def _csv_read_spares(file) -> List[SpareItem]:
    try:
        content = file.read().decode("utf-8", errors="ignore")
        rd = csv.DictReader(io.StringIO(content))
        out: List[SpareItem] = []
        for i, r in enumerate(rd, 1):
            out.append(SpareItem(
                id=(r.get("id") or f"S-{i:04d}").strip(),
                part_no=(r.get("part_no") or "").strip(),
                description=(r.get("description") or "").strip(),
                vendor=(r.get("vendor") or "").strip(),
                location=(r.get("location") or "").strip(),
                quantity=int((r.get("quantity") or 0) or 0),
                min_qty=int((r.get("min_qty") or 0) or 0),
                lead_time_days=int((r.get("lead_time_days") or 0) or 0),
                notes=(r.get("notes") or "").strip(),
            ))
        return out
    except Exception as e:
        st.error(f"Spares CSV parse error: {e}")
        return []


# ---------- Metrics ----------
def _warranty_metrics(items: List[WarrantyItem]) -> Dict[str, Any]:
    today = date.today().isoformat()
    total = len(items)
    expiring_90 = 0
    expired = 0
    by_vendor: Dict[str, int] = {}
    for it in items:
        if it.vendor:
            by_vendor[it.vendor] = by_vendor.get(it.vendor, 0) + 1
        if it.end_date:
            d = _days(today, _safe_date(it.end_date))
            if isinstance(d, int):
                if d < 0:
                    expired += 1
                elif d <= 90:
                    expiring_90 += 1
    return {"total": total, "expiring_90": expiring_90, "expired": expired, "by_vendor": by_vendor}

def _spares_metrics(items: List[SpareItem]) -> Dict[str, Any]:
    total_parts = len(items)
    total_qty = sum(int(it.quantity or 0) for it in items)
    below_min = sum(1 for it in items if int(it.quantity or 0) < int(it.min_qty or 0))
    return {"total_parts": total_parts, "total_qty": total_qty, "below_min": below_min}


# ---------- Main ----------
def run(project_id: str | None = None, phase_id: str | None = None):
    st.subheader("Warranties & Spares")

    pid  = project_id or st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = phase_id   or st.session_state.get("current_phase_id", "PH-FEL1")

    # Load latest artifacts
    w_latest = get_latest(pid, ART_WARRANTIES, phid)
    s_latest = get_latest(pid, ART_SPARES, phid)
    w_items: List[WarrantyItem] = []
    s_items: List[SpareItem] = []
    if w_latest:
        w_items = [WarrantyItem(**r) for r in (w_latest.get("data", {}) or {}).get("rows", []) if r.get("id")]
    if s_latest:
        s_items = [SpareItem(**r) for r in (s_latest.get("data", {}) or {}).get("rows", []) if r.get("id")]

    # Session state
    w_key = _keyify("warranty_rows", pid, phid)
    s_key = _keyify("spares_rows", pid, phid)
    if w_key not in st.session_state:
        st.session_state[w_key] = w_items or [
            WarrantyItem(id="W-0001", asset="AHU-01", vendor="CoolTech", serial="CT-1234",
                         start_date=date.today().isoformat(),
                         end_date=date.today().isoformat(), terms="1 year parts/labor", contact="support@cooltech.com"),
        ]
    if s_key not in st.session_state:
        st.session_state[s_key] = s_items or [
            SpareItem(id="S-0001", part_no="FLT-16x20x2", description="Filter 16x20x2", vendor="HVAC Supply",
                      location="Store A / Rack 3", quantity=6, min_qty=10, lead_time_days=7),
        ]

    tab_w, tab_s = st.tabs(["Warranties", "Spares"])

    # ---------- Warranties tab ----------
    with tab_w:
        with st.expander("📄 Import / Export (Warranties)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                up = st.file_uploader("Import CSV", type=["csv"], key=_keyify("w_imp", pid, phid))
                if up is not None:
                    parsed = _csv_read_warranties(up)
                    if parsed:
                        st.session_state[w_key] = parsed
                        st.success(f"Imported {len(parsed)} warranties.")
            with c2:
                st.download_button(
                    "Download CSV",
                    data=_csv_write([x.to_dict() for x in st.session_state[w_key]], W_FIELDS),
                    file_name=f"{pid}_{phid}_warranties.csv",
                    mime="text/csv",
                    key=_keyify("w_exp", pid, phid),
                )

        m = _warranty_metrics(st.session_state[w_key])
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total", m["total"])
        with c2: st.metric("Expiring ≤ 90d", m["expiring_90"])
        with c3: st.metric("Expired", m["expired"])
        if m["by_vendor"]:
            st.caption("By vendor: " + ", ".join(f"{k}:{v}" for k, v in sorted(m["by_vendor"].items())))

        f1, f2, f3 = st.columns([2,1,1])
        with f1:
            f_text = st.text_input("Filter (asset/vendor/serial/notes)", key=_keyify("w_ft", pid, phid))
        with f2:
            f_vendor = st.text_input("Vendor", key=_keyify("w_v", pid, phid))
        with f3:
            status_opt = ["All","Active","Expiring≤90d","Expired"]
            f_status = st.selectbox("Status", status_opt, index=0, key=_keyify("w_st", pid, phid))

        def _w_visible(x: WarrantyItem) -> bool:
            txt = (f_text or "").lower().strip()
            if txt:
                blob = " ".join([x.id, x.asset, x.vendor, x.serial, x.notes]).lower()
                if txt not in blob:
                    return False
            if f_vendor and f_vendor.lower().strip() not in (x.vendor or "").lower():
                return False
            if f_status != "All" and x.end_date:
                t = _days(date.today().isoformat(), _safe_date(x.end_date))
                if f_status == "Expired" and not (isinstance(t, int) and t < 0): return False
                if f_status == "Expiring≤90d" and not (isinstance(t, int) and 0 <= t <= 90): return False
                if f_status == "Active" and not (isinstance(t, int) and t > 90): return False
            return True

        a1, a2 = st.columns([1,1])
        with a1:
            if st.button("➕ Add warranty", key=_keyify("w_add", pid, phid)):
                n = len(st.session_state[w_key]) + 1
                st.session_state[w_key].append(WarrantyItem(id=f"W-{n:04d}"))
        with a2:
            if st.button("🗑️ Remove last", key=_keyify("w_del", pid, phid)):
                if st.session_state[w_key]:
                    st.session_state[w_key].pop()

        for i, w in enumerate(st.session_state[w_key]):
            if not _w_visible(w): continue
            with st.expander(f"{w.id} · {w.asset or w.vendor} · {w.end_date or 'no end'}", expanded=False):
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    w.id = st.text_input("ID", w.id, key=_keyify("w_id", pid, phid, i))
                    w.asset = st.text_input("Asset/System", w.asset, key=_keyify("w_asset", pid, phid, i))
                    w.vendor = st.text_input("Vendor", w.vendor, key=_keyify("w_vendor", pid, phid, i))
                    w.serial = st.text_input("Serial", w.serial, key=_keyify("w_serial", pid, phid, i))
                with c2:
                    w.start_date = st.text_input("Start (YYYY-MM-DD)", w.start_date, key=_keyify("w_sd", pid, phid, i))
                    w.end_date   = st.text_input("End (YYYY-MM-DD)",   w.end_date,   key=_keyify("w_ed", pid, phid, i))
                    w.contact    = st.text_input("Support contact", w.contact, key=_keyify("w_ct", pid, phid, i))
                with c3:
                    w.terms = st.text_area("Terms", w.terms, key=_keyify("w_terms", pid, phid, i))
                    w.attachments = _listify(st.text_area("Attachments (comma/newline)", ", ".join(w.attachments or []),
                                                          key=_keyify("w_att", pid, phid, i)))
                w.notes = st.text_area("Notes", w.notes, key=_keyify("w_notes", pid, phid, i))

        st.divider()
        w_payload = {"rows": [x.to_dict() for x in st.session_state[w_key]],
                     "saved_at": datetime.utcnow().isoformat() + "Z"}
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Save Warranties (Draft)", key=_keyify("w_save_d", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_WARRANTIES, w_payload, status="Draft")
                st.success("Warranties saved (Draft).")
        with b2:
            if st.button("Save Warranties (Pending)", key=_keyify("w_save_p", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_WARRANTIES, w_payload, status="Pending")
                st.success("Warranties saved (Pending).")
        with b3:
            if st.button("Save & Approve Warranties", key=_keyify("w_save_a", pid, phid)):
                rec = save_artifact(pid, phid, WORKSTREAM, ART_WARRANTIES, w_payload, status="Pending")
                try:
                    from artifact_registry import approve_artifact
                    approve_artifact(pid, rec.get("artifact_id"))
                except Exception:
                    pass
                st.success("Warranties saved and Approved.")

    # ---------- Spares tab ----------
    with tab_s:
        with st.expander("📄 Import / Export (Spares)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                up = st.file_uploader("Import CSV", type=["csv"], key=_keyify("s_imp", pid, phid))
                if up is not None:
                    parsed = _csv_read_spares(up)
                    if parsed:
                        st.session_state[s_key] = parsed
                        st.success(f"Imported {len(parsed)} spares.")
            with c2:
                st.download_button(
                    "Download CSV",
                    data=_csv_write([x.to_dict() for x in st.session_state[s_key]], S_FIELDS),
                    file_name=f"{pid}_{phid}_spares.csv",
                    mime="text/csv",
                    key=_keyify("s_exp", pid, phid),
                )

        m = _spares_metrics(st.session_state[s_key])
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total parts", m["total_parts"])
        with c2: st.metric("Total qty",   m["total_qty"])
        with c3: st.metric("Below min",   m["below_min"])

        f1, f2 = st.columns([2,1])
        with f1:
            sf_text = st.text_input("Filter (part/desc/vendor/location)", key=_keyify("s_ft", pid, phid))
        with f2:
            show_only_low = st.checkbox("Only below min", value=False, key=_keyify("s_low", pid, phid))

        def _s_visible(x: SpareItem) -> bool:
            if show_only_low and int(x.quantity or 0) >= int(x.min_qty or 0):
                return False
            txt = (sf_text or "").lower().strip()
            if txt:
                blob = " ".join([x.id, x.part_no, x.description, x.vendor, x.location, x.notes]).lower()
                if txt not in blob:
                    return False
            return True

        a1, a2 = st.columns([1,1])
        with a1:
            if st.button("➕ Add spare", key=_keyify("s_add", pid, phid)):
                n = len(st.session_state[s_key]) + 1
                st.session_state[s_key].append(SpareItem(id=f"S-{n:04d}"))
        with a2:
            if st.button("🗑️ Remove last", key=_keyify("s_del", pid, phid)):
                if st.session_state[s_key]:
                    st.session_state[s_key].pop()

        for i, s in enumerate(st.session_state[s_key]):
            if not _s_visible(s): continue
            low_flag = int(s.quantity or 0) < int(s.min_qty or 0)
            with st.expander(f"{s.id} · {s.part_no or s.description} · qty {s.quantity}" + (" · ⚠️ low" if low_flag else ""),
                             expanded=False):
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    s.id = st.text_input("ID", s.id, key=_keyify("s_id", pid, phid, i))
                    s.part_no = st.text_input("Part No.", s.part_no, key=_keyify("s_pn", pid, phid, i))
                    s.description = st.text_input("Description", s.description, key=_keyify("s_desc", pid, phid, i))
                with c2:
                    s.vendor = st.text_input("Vendor", s.vendor, key=_keyify("s_vendor", pid, phid, i))
                    s.location = st.text_input("Location", s.location, key=_keyify("s_loc", pid, phid, i))
                with c3:
                    s.quantity = st.number_input("Quantity", 0, value=int(s.quantity or 0), key=_keyify("s_qty", pid, phid, i))
                    s.min_qty  = st.number_input("Min qty", 0, value=int(s.min_qty or 0), key=_keyify("s_minq", pid, phid, i))
                    s.lead_time_days = st.number_input("Lead time (days)", 0, value=int(s.lead_time_days or 0),
                                                       key=_keyify("s_lead", pid, phid, i))
                s.notes = st.text_area("Notes", s.notes, key=_keyify("s_notes", pid, phid, i))

        st.divider()
        s_payload = {"rows": [x.to_dict() for x in st.session_state[s_key]],
                     "saved_at": datetime.utcnow().isoformat() + "Z"}
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Save Spares (Draft)", key=_keyify("s_save_d", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_SPARES, s_payload, status="Draft")
                st.success("Spares saved (Draft).")
        with b2:
            if st.button("Save Spares (Pending)", key=_keyify("s_save_p", pid, phid)):
                save_artifact(pid, phid, WORKSTREAM, ART_SPARES, s_payload, status="Pending")
                st.success("Spares saved (Pending).")
        with b3:
            if st.button("Save & Approve Spares", key=_keyify("s_save_a", pid, phid)):
                rec = save_artifact(pid, phid, WORKSTREAM, ART_SPARES, s_payload, status="Pending")
                try:
                    from artifact_registry import approve_artifact
                    approve_artifact(pid, rec.get("artifact_id"))
                except Exception:
                    pass
                st.success("Spares saved and Approved.")
