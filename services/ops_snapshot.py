# services/ops_snapshot.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, Any
import pandas as pd

from data.firestore import load_project_doc, save_project_doc

def _safe(username: str, namespace: str, project_id: str, key: str) -> Dict[str, Any]:
    try:
        return load_project_doc(username, namespace, project_id, key) or {}
    except Exception:
        return {}

def rebuild_snapshot(username: str, namespace: str, project_id: str) -> Dict[str, Any]:
    """Build and persist a compact Ops snapshot for the current namespace.
    Writes to the doc key the sidebar expects: f"{industry}_ops_{ops_mode}".
    """
    try:
        industry, _, ops_mode = (namespace or "manufacturing:ops:daily_ops").split(":", 2)
    except Exception:
        industry, ops_mode = "manufacturing", "daily_ops"
    out_key = f"{industry}_ops_{ops_mode}"

    snap: Dict[str, Any] = {
        "meta": {
            "generated_at": datetime.utcnow().isoformat(),
            "namespace": namespace,
            "project_id": project_id,
            "ops_mode": ops_mode,
        },
        "daily_ops": {},
        "small_projects": {},
    }

    # ---------- DAILY OPS ----------
    if ops_mode == "daily_ops":
        andon = _safe(username, namespace, project_id, "andon_log")
        if andon:
            k = andon.get("kpis", {})
            snap["daily_ops"]["andon"] = {
                "incidents": k.get("incidents"),
                "downtime_min": k.get("downtime"),
                "mttr_min": k.get("mttr"),
                "critical": k.get("critical"),
                "open": k.get("open"),
            }
                # Shift Huddle Board
        huddle = _safe(username, namespace, project_id, "shift_huddle")
        if huddle:
            snap["daily_ops"]["huddle"] = huddle.get("metrics", {})

        # CMMS (Lite)
        cmms = _safe(username, namespace, project_id, "cmms_lite")
        if cmms:
            snap["daily_ops"]["cmms"] = cmms.get("metrics", {})

        # SPC Monitor (Lite)
        spc = _safe(username, namespace, project_id, "spc_monitor")
        if spc:
            m = spc.get("metrics", {})
            if not m:
                import pandas as pd
                d = pd.DataFrame(spc.get("rows", []))
                if not d.empty:
                    d["Sample"] = pd.to_numeric(d.get("Sample", 0), errors="coerce").fillna(0.0)
                    d["LSL"] = pd.to_numeric(d.get("LSL", 0), errors="coerce").fillna(0.0)
                    d["USL"] = pd.to_numeric(d.get("USL", 0), errors="coerce").fillna(0.0)
                    m = {
                        "stations": int(d["Station"].nunique()),
                        "avg_yield": float(
                            (d["Sample"].between(d["LSL"], d["USL"])).mean() * 100.0
                        ),
                    }
            snap["daily_ops"]["spc"] = m

        # OEE Board (latest saved metrics)
        oee = _safe(username, namespace, project_id, "oee_board")
        if oee:
            snap["daily_ops"]["oee"] = oee.get("metrics", {})
        # SMT Feeder Setup (Electronics)
        smt = _safe(username, namespace, project_id, "smt_feeder_setup")
        if smt:
            m = smt.get("metrics", {})
            if not m:
                # derive minimal metrics from rows
                import pandas as pd
                df = pd.DataFrame(smt.get("rows", []))
                if not df.empty:
                    df["Missing Reel"] = df.get("Missing Reel", False).astype(bool)
                    df["Setup (min)"] = pd.to_numeric(df.get("Setup (min)", 0), errors="coerce").fillna(0)
                    m = {
                        "setups": len(df),
                        "total_setup": int(df["Setup (min)"].sum()),
                        "avg_setup": float(df["Setup (min)"].mean()) if len(df) else 0.0,
                        "missing": int(df["Missing Reel"].sum()),
                    }
            snap["daily_ops"]["smt_feeder"] = m

        # FPY Dashboard (Electronics)
        fpy = _safe(username, namespace, project_id, "fpy_dashboard")
        if fpy:
            snap["daily_ops"]["fpy"] = {"overall_fpy": fpy.get("overall_fpy")}
        # OTIF Tracker (Supply Chain)
        otif = _safe(username, namespace, project_id, "otif_tracker")
        if otif:
            m = otif.get("metrics", {})
            if not m:
                df = pd.DataFrame(otif.get("rows", []))
                if not df.empty:
                    # recompute quickly if saved without metrics
                    df["On-time"] = pd.to_datetime(df.get("Delivered Date")) <= pd.to_datetime(df.get("Promise Date"))
                    df["In-full"] = pd.to_numeric(df.get("Qty Delivered", 0), errors="coerce").fillna(0) >= pd.to_numeric(df.get("Qty Ordered", 0), errors="coerce").fillna(0)
                    df["OTIF"] = df["On-time"] & df["In-full"]
                    tot = len(df)
                    if tot > 0:
                        m = {
                            "orders": tot,
                            "on_time_pct": round(100.0 * df["On-time"].mean(), 1),
                            "in_full_pct": round(100.0 * df["In-full"].mean(), 1),
                            "otif_pct": round(100.0 * df["OTIF"].mean(), 1),
                            "late_count": int((~df["On-time"]).sum()),
                            "short_count": int((~df["In-full"]).sum()),
                        }
            snap["daily_ops"]["otif"] = m

        # Kanban Replenishment (Supply Chain)
        kanban = _safe(username, namespace, project_id, "kanban_replenishment")
        if kanban:
            m = kanban.get("metrics", {})
            if not m:
                d = pd.DataFrame(kanban.get("rows", []))
                if not d.empty:
                    for c in ("Min","Max","On Hand","In Transit","Card Size"):
                        d[c] = pd.to_numeric(d.get(c, 0), errors="coerce").fillna(0)
                    d["Available"] = d["On Hand"] + d["In Transit"]
                    m = {
                        "sku": len(d),
                        "shortages": int((d["Available"] < d["Min"]).sum()),
                        "to_order": int((d["Max"] - d["Available"]).clip(lower=0).gt(0).sum()),
                        "reorder_total": int((d["Max"] - d["Available"]).clip(lower=0).sum()),
                    }
            snap["daily_ops"]["kanban"] = m

    # ---------- SMALL PROJECTS ----------
    if ops_mode == "small_projects":
        smed = _safe(username, namespace, project_id, "smed_changeover")
        if smed:
            t = smed.get("totals", {})
            snap["small_projects"]["smed"] = {
                "product": smed.get("meta", {}).get("product"),
                "internal_min": t.get("internal"),
                "external_min": t.get("external"),
                "total_min": t.get("total"),
                "saved_est_min": t.get("saved_est"),
                "new_changeover_est_min": t.get("new_changeover_est"),
            }
        # Milk-Run Route Builder (Supply Chain small-project)
        milk = _safe(username, namespace, project_id, "milk_run_builder")
        if milk:
            m = milk.get("metrics", {})
            if not m:
                import pandas as pd
                df = pd.DataFrame(milk.get("rows", []))
                if not df.empty:
                    for c in ("Distance to next (km)", "Dwell (min)", "Max Pallets"):
                        df[c] = pd.to_numeric(df.get(c, 0), errors="coerce").fillna(0)
                    m = {
                        "stops": len(df),
                        "pallets_used": int(df["Max Pallets"].sum()),
                        "route_km": float(pd.to_numeric(df["Distance to next (km)"], errors="coerce").fillna(0).sum()),
                        "dwell_min": int(pd.to_numeric(df["Dwell (min)"], errors="coerce").fillna(0).sum()),
                    }
            snap["small_projects"]["milk_run"] = m

        # Supplier Development A3 (Supply Chain small-project)
        a3 = _safe(username, namespace, project_id, "supplier_dev_a3")
        if a3:
            s = a3.get("a3", {})
            snap["small_projects"]["supplier_a3"] = {
                "supplier": s.get("Supplier"),
                "part": s.get("Part"),
                "otd_pct": s.get("OTD %"),
                "ppm": s.get("PPM"),
                "lead_time_d": s.get("Lead-time (d)"),
            }

        kaizen = _safe(username, namespace, project_id, "kaizen_tracker")
        if kaizen:
            m = kaizen.get("metrics", {})
            snap["small_projects"]["kaizen"] = {
                "ideas": sum(m.get("counts", {}).values()) if m.get("counts") else None,
                "monthly_benefit": m.get("monthly_total"),
                "oneoff_cost": m.get("oneoff_total"),
                "payback_months": m.get("payback"),
                "roi_annual_pct": m.get("roi_annual"),
            }

        risk = _safe(username, namespace, project_id, "risk_lite")
        if risk:
            df = pd.DataFrame(risk.get("rows", []))
            if not df.empty:
                df["Exposure"] = pd.to_numeric(df.get("Exposure", 0), errors="coerce").fillna(0)
                snap["small_projects"]["risk"] = {
                    "open": int((df.get("Status", "") == "Open").sum()),
                    "exposure_sum": int(df["Exposure"].sum()),
                    "max_exposure": int(df["Exposure"].max()),
                }

        msb = _safe(username, namespace, project_id, "mini_scope_builder")
        if msb:
            df = pd.DataFrame(msb.get("rows", []))
            if not df.empty:
                start = pd.to_datetime(df.get("Start"), errors="coerce")
                finish = pd.to_datetime(df.get("Finish"), errors="coerce")
                snap["small_projects"]["scope"] = {
                    "tasks": int(len(df)),
                    "started": str(start.min().date()) if start.notna().any() else None,
                    "finish": str(finish.max().date()) if finish.notna().any() else None,
                    "done": int((df.get("Status") == "Done").sum()) if "Status" in df.columns else None,
                }

        lws = _safe(username, namespace, project_id, "lightweight_schedule")
        if lws:
            df = pd.DataFrame(lws.get("rows", []))
            snap["small_projects"]["schedule"] = {"tasks": int(len(df))}

    # Persist snapshot
    save_project_doc(username, namespace, project_id, out_key, snap)
    return snap
