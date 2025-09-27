# workflows/pm_hub_arch_construction.py
from typing import Dict, Any, Optional, Tuple, List
import importlib
import re
import streamlit as st

# ---------------- Streamlit compatibility ----------------
def _safe_rerun():
    """Use st.rerun() on modern Streamlit; fall back to experimental on older."""
    rr = getattr(st, "rerun", None)
    if callable(rr):
        rr(); return
    rr_old = getattr(st, "experimental_rerun", None)
    if callable(rr_old):
        rr_old()

# ---------------- key helper (avoid duplicate keys globally) ----------------
def _keyify(*parts: Any) -> str:
    def clean(x: Any) -> str:
        s = str(x)
        return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip("_")
    return "_".join(clean(p) for p in parts if p is not None and str(p) != "")

# ---------------- soft imports so this hub never crashes ----------------
def _soft_import(path: str, attr: str, msg: str = "panel not available."):
    try:
        mod = importlib.import_module(path)
        fn = getattr(mod, attr, None)
        return fn if callable(fn) else (lambda *a, **k: st.caption(f"{attr} {msg}"))
    except Exception:
        return lambda *a, **k: st.caption(f"{attr} {msg}")

render_stakeholders_panel   = _soft_import("workflows.pm_common.stakeholders", "render_stakeholders_panel")
render_moc_panel            = _soft_import("workflows.pm_common.moc", "render_moc_panel")
render_action_tracker_panel = _soft_import("workflows.pm_common.action_tracker", "render_action_tracker_panel")

def _soft(attr_path: Tuple[str, str], fallback=None):
    mod_path, attr = attr_path
    try:
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr)
    except Exception:
        return fallback

compute_pm_kpis    = _soft(("services.kpis", "compute_pm_kpis"), lambda *_a, **_k: {})
render_pm_overview = _soft(("services.overview", "render_pm_overview"), lambda *_a, **_k: st.caption("Overview not available."))
list_req_industry  = _soft(("services.industry_gate_requirements", "list_required_artifacts_industry_aware"), lambda *_a, **_k: [])
get_latest         = _soft(("artifact_registry", "get_latest"))
approve_artifact   = _soft(("artifact_registry", "approve_artifact"))
save_artifact      = _soft(("artifact_registry", "save_artifact"))

# ---------------- Module aliasing (points hub cards to actual modules) ----------------
# As we create each module, keep its alias here so the Hub card opens it.
MODULE_ALIASES = {
    # FEL1 – Concept
    "workflows.modules.program_brief":        "workflows.pm_arch_construction.program_brief",
    "workflows.modules.site_screener":        "workflows.pm_arch_construction.site_screener",
    "workflows.modules.permitting":           "workflows.pm_arch_construction.permitting",
    "workflows.modules.concept_kit":          "workflows.pm_arch_construction.concept_kit",
    "workflows.modules.parking_sizing":       "workflows.pm_arch_construction.parking_sizing",

    # FEL2 – Design
    "workflows.modules.bim_lite":             "workflows.pm_arch_construction.bim_lite",
    "workflows.modules.footprint_estimator":  "workflows.pm_arch_construction.footprint_estimator",
    "workflows.modules.rom_cost_model":       "workflows.pm_arch_construction.rom_cost_model",
    "workflows.modules.schedule_l2l3_draft":  "workflows.pm_arch_construction.schedule_l2l3_draft",
    "workflows.modules.design_reviews":       "workflows.pm_arch_construction.design_reviews",
    "workflows.modules.clash_log":            "workflows.pm_arch_construction.clash_log",
    "workflows.modules.value_engineering":    "workflows.pm_arch_construction.value_engineering",
    "workflows.modules.cost_library":         "workflows.pm_arch_construction.cost_library",

    # FEL3 – Execution
    "workflows.modules.schedule_dev":         "workflows.pm_arch_construction.schedule_dev",
    "workflows.modules.procurement":          "workflows.pm_arch_construction.procurement",
    "workflows.modules.lookahead":            "workflows.pm_arch_construction.lookahead",
    "workflows.modules.earned_value":         "workflows.pm_arch_construction.earned_value",
    "workflows.modules.rfi_submittals":       "workflows.pm_arch_construction.rfi_submittals",
    "workflows.modules.change_orders":        "workflows.pm_arch_construction.change_orders",

    # IMPORTANT: map 'quality' → our QA/QC module
    "workflows.modules.quality":              "workflows.pm_arch_construction.qaqc",
    # also allow explicit alias if used anywhere
    "workflows.modules.qaqc":                 "workflows.pm_arch_construction.qaqc",

    "workflows.modules.hse":                  "workflows.pm_arch_construction.hse",

    # FEL4 – Handover
    "workflows.modules.commissioning":        "workflows.pm_arch_construction.commissioning",
    "workflows.modules.punchlist":            "workflows.pm_arch_construction.punchlist",
    "workflows.modules.warranty_spares":      "workflows.pm_arch_construction.warranty_spares",
    "workflows.modules.handover_asbuilt":     "workflows.pm_arch_construction.handover_asbuilt",
}

def _candidates(alias: str) -> List[str]:
    real = MODULE_ALIASES.get(alias)
    return [real, alias] if real else [alias]

def _import_first(paths: List[str], entry: str = "run"):
    """Try importing first working (module, callable = run()/render())."""
    last_err = None
    for p in paths:
        try:
            mod = importlib.import_module(p)
            fn = getattr(mod, entry, getattr(mod, "render", None))
            if callable(fn):
                return mod, fn, p
        except Exception as e:
            last_err = e
            continue
    return None, None, last_err

# ---------------- Workspace opener ----------------
def _open_workspace():
    """Open the Architecture & Construction workspace using your dynamic opener."""
    try:
        from services.workspace_openers import open_pm_workspace
        open_pm_workspace("arch_construction", st.session_state.get("fel_stage", "FEL1"), None)
        return
    except Exception:
        pass
    try:
        from services.industries import route as industries_route
        module_path, entry = industries_route("arch_construction", "projects")
        mod = importlib.import_module(module_path)
        fn = getattr(mod, entry or "run", getattr(mod, "run", None))
        if callable(fn):
            fn(); return
    except Exception as e:
        st.warning(f"Could not open workspace automatically: {e}")

# ---------------- Card → artifacts mapping (for status chips) ----------------
# If a card represents multiple artifacts, we show:
#   Approved → all approved; Pending → at least one exists but not all approved; Missing → some missing
CARD_ARTIFACTS: Dict[str, List[str]] = {
    # FEL1
    "Program Brief / Business Case": ["Program_Brief"],
    "Site Screener":                 ["Site_Screener"],
    "Permitting & Zoning":           ["Permitting_Checklist"],
    "Concept Design Kit":            ["Concept_Design_Kit"],   # ← align with requirements
    "Parking Sizing":                ["Parking_Sizing"],

    # FEL2
    "BIM-lite Tracker":              ["BIM_Lite"],
    "Footprint Estimator":           ["Footprint_Estimate"],
    "ROM Cost Snapshot":             ["ROM_Cost_Model"],
    "L2/L3 Schedule Draft":          ["L2_L3_Schedule_Draft"],
    "Design Review Matrix":          ["Design_Issue_Log"],
    "Clash Log (CSV/Import)":        ["Clash_Log"],
    "Value Engineering (VE) Log":    ["VE_Log"],
    "Cost Library & Escalation":     ["Unit_Rate_Library"],

    # FEL3
    "Schedule (WBS + Network)":      ["WBS", "Schedule_Network"],
    "Procurement Packages":          ["Procurement_Packages", "Long_Lead_Items"],
    "2–6 Week Lookahead":            ["Lookahead_Plan"],
    # IMPORTANT: Use artifacts produced by our QA/QC module
    "QA/QC Inspections":             ["QAQC_Inspections", "NCR_Log"],
    # IMPORTANT: Use artifacts produced by our EV module
    "Earned Value (EV)":             ["EV_Snapshot", "EV_Timeseries"],
    "RFI & Submittals":              ["RFI_Log", "Submittal_Log"],
    "Change Orders":                 ["Change_Order_Log"],
    "HSE (Toolbox/Incidents)":       ["HSE_Toolbox_Log", "Incident_Log"],

    # FEL4
    "Commissioning Tracker":         ["Cx_Systems", "PreFunc_Checks", "Func_Tests", "Defect_Log"],
    "Punchlist (Closeout)":          ["Punchlist_Log"],
    "Warranties & Spares":           ["Warranties", "Spares_List"],
    "As-Built / O&M / Handover":     ["AsBuilt_OM"],
}

def _artifact_status(types: List[str]) -> str:
    """Return Approved / Pending / Missing for a set of artifact types (latest per type)."""
    if not get_latest:
        return "Unknown"
    pid  = st.session_state.get("current_project_id", "P-AC-DEMO")
    phid = st.session_state.get("current_phase_id",  "PH-FEL1")
    saw_any = False
    any_pending = False
    for t in types:
        rec = get_latest(pid, t, phid)
        if rec:
            saw_any = True
            if rec.get("status") != "Approved":
                any_pending = True
        else:
            return "Missing"
    if not saw_any:
        return "Missing"
    return "Pending" if any_pending else "Approved"

def _badge(status: str):
    if status == "Approved":
        st.success("Approved", icon="✅")
    elif status == "Pending":
        st.warning("Pending", icon="⏳")
    elif status == "Missing":
        st.error("Missing", icon="❌")
    else:
        st.info(status)

# ---------------- stages (FEL1–FEL4; all features wired) ----------------
STAGES: Dict[str, Dict[str, Any]] = {
    "fel1": {
        "label": "Concept",
        "cards": [
            ("Program Brief / Business Case", "workflows.modules.program_brief"),
            ("Site Screener",                 "workflows.modules.site_screener"),
            ("Permitting & Zoning",           "workflows.modules.permitting"),
            ("Concept Design Kit",            "workflows.modules.concept_kit"),   # massing/quick calcs
            ("Parking Sizing",                "workflows.modules.parking_sizing"),
        ],
    },
    "fel2": {
        "label": "Design",
        "cards": [
            ("BIM-lite Tracker",      "workflows.modules.bim_lite"),
            ("Footprint Estimator",   "workflows.modules.footprint_estimator"),
            ("ROM Cost Snapshot",     "workflows.modules.rom_cost_model"),
            ("L2/L3 Schedule Draft",  "workflows.modules.schedule_l2l3_draft"),
            ("Design Review Matrix",  "workflows.modules.design_reviews"),
            ("Clash Log (CSV/Import)","workflows.modules.clash_log"),
            ("Value Engineering (VE) Log", "workflows.modules.value_engineering"),
            ("Cost Library & Escalation",  "workflows.modules.cost_library"),
        ],
    },
    "fel3": {
        "label": "Execution",
        "cards": [
            ("Schedule (WBS + Network)", "workflows.modules.schedule_dev"),
            ("Procurement Packages",     "workflows.modules.procurement"),
            ("2–6 Week Lookahead",       "workflows.modules.lookahead"),
            ("QA/QC Inspections",        "workflows.modules.qaqc"),         # ← use our QA/QC module
            ("Earned Value (EV)",        "workflows.modules.earned_value"), # ← EV module
            ("RFI & Submittals",         "workflows.modules.rfi_submittals"),
            ("Change Orders",            "workflows.modules.change_orders"),
            ("HSE (Toolbox/Incidents)",  "workflows.modules.hse"),
        ],
    },
    "fel4": {
        "label": "Handover",
        "cards": [
            ("Commissioning Tracker",        "workflows.modules.commissioning"),
            ("Punchlist (Closeout)",         "workflows.modules.punchlist"),
            ("Warranties & Spares",          "workflows.modules.warranty_spares"),
            ("As-Built / O&M / Handover",    "workflows.modules.handover_asbuilt"),
        ],
    },
}

# ---------------- Launch helpers ----------------
def _launch(title: str, target: str, key_prefix: str):
    """
    Launch a tool or workspace.
    - 'workspace:<hint>' → open the A&C workspace.
    - else import a module and call run()/render().
    Shows a status badge for mapped artifacts.
    """
    # status chip
    arts = CARD_ARTIFACTS.get(title, [])
    if arts:
        _badge(_artifact_status(arts))

    # launch button with safe, namespaced key
    label = f"Open · {title}"
    if target.startswith("workspace:"):
        if st.button(label, key=_keyify("ac_hub", "open", key_prefix, title, target)):
            _open_workspace()
        return

    _m, fn, _ = _import_first(_candidates(target))
    if callable(fn):
        if st.button(label, key=_keyify("ac_hub", "open", key_prefix, title, target)):
            fn()
    else:
        st.button(label, key=_keyify("ac_hub", "open_dis", key_prefix, title, target), disabled=True)
        tried = ", ".join(_candidates(target))
        st.caption(f"*Not available yet.* Tried: {tried}")

# ---------------- Main render ----------------
def render(T: Optional[Dict[str, Any]] = None):
    st.header("🏛️ PM Hub — Architecture & Construction")

    # Sidebar KPI inputs
    with st.sidebar.expander("📁 Project Data", expanded=True):
        capex  = st.number_input("CAPEX (M$)", 0.0, value=float(st.session_state.get("capex", 50.0)))
        opex   = st.number_input("OPEX (M$/y)", 0.0, value=float(st.session_state.get("opex", 5.0)))
        months = st.number_input("Schedule (months)", 0.0, value=float(st.session_state.get("months", 24.0)))
        risk   = st.slider("Risk Index", 0.0, 10.0, float(st.session_state.get("risk", 4.0)))

    # Keep these available for downstream modules (e.g., EV baseline)
    st.session_state["capex"]  = capex
    st.session_state["opex"]   = opex
    st.session_state["months"] = months
    st.session_state["risk"]   = risk

    # KPIs (safe if compute_pm_kpis missing)
    _ = compute_pm_kpis({"capex": capex, "opex": opex, "schedule_months": months, "risk_score": risk})

    tabs = st.tabs(["Overview", "FEL Swimlane", "Stage-Gate"])

    # -------- Overview --------
    with tabs[0]:
        render_pm_overview({
            "capex": capex,
            "opex": opex,
            "schedule_months": months,
            "risk_score": risk,
            "fel_stage": st.session_state.get("fel_stage", "FEL1"),
        })
        st.markdown("### Cross-Industry Panels")
        render_stakeholders_panel()
        render_moc_panel()
        render_action_tracker_panel()

    # -------- Swimlane --------
    with tabs[1]:
        st.markdown("### Architecture & Construction Swimlane")
        cols = st.columns(len(STAGES))
        for i, (code, meta) in enumerate(STAGES.items()):
            with cols[i]:
                st.subheader(meta["label"])
                for j, (title, target) in enumerate(meta["cards"]):
                    lc, rc = st.columns([1, 2])
                    with lc:
                        pass  # status is rendered above
                    with rc:
                        _launch(title, target, key_prefix=f"{code}_{j}")

    # -------- Stage-Gate --------
    with tabs[2]:
        st.subheader("Stage-Gate Checklist")
        industry   = "arch_construction"
        phase_code = st.session_state.get("fel_stage", "FEL1")

        reqs = list_req_industry(phase_code, industry) or []
        if not reqs:
            st.caption("No registered requirements for this phase.")
            return

        pid  = st.session_state.get("current_project_id", "P-AC-DEMO")
        phid = st.session_state.get("current_phase_id",  f"PH-{phase_code}")

        done = 0
        cols = st.columns(2)
        for i, r in enumerate(reqs):
            ws  = r.get("workstream", "?")
            typ = r.get("type", "?")
            rec = get_latest(pid, typ, phid) if get_latest else None
            status = (rec or {}).get("status", "Missing")

            with cols[i % 2]:
                st.write(f"**{ws} → {typ}**")
                _badge("Approved" if status == "Approved"
                       else "Pending" if status == "Pending"
                       else "Missing")

                # Unique, namespaced keys to avoid conflicts with Pipeline checklist etc.
                approve_key = _keyify("ac_hub", "approve", phase_code, pid, phid, typ, i)
                seed_key    = _keyify("ac_hub", "seed",    phase_code, pid, phid, typ, i)

                if status == "Pending" and approve_artifact:
                    if st.button(f"Approve {typ}", key=approve_key):
                        try:
                            approve_artifact(pid, rec["artifact_id"])
                        finally:
                            _safe_rerun()

                if status == "Missing" and save_artifact:
                    if st.button(f"Seed {typ} (Draft)", key=seed_key):
                        try:
                            save_artifact(pid, phid, ws, typ, {"seed": True}, status="Draft")
                        finally:
                            _safe_rerun()

                if status == "Approved":
                    done += 1

        st.caption(f"Progress: {done}/{len(reqs)} approved")
