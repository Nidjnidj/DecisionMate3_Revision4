# ============================ demo_usage.py (optional) ============================
from __future__ import annotations
from datetime import date

from .artifact_service import ArtifactService
from .schemas import (
    ReservoirProfiles, ReservoirPoint,
    FacilityLoads, FacilityLoadsPoint,
    EquipmentSizingList, EquipmentSizingItem,
    LLICandidates, LLICandidate,
    WBSActivities, WBSActivity
)

if __name__ == "__main__":
    svc = ArtifactService()




    # 1) Subsurface registers reservoir profiles + facility loads
    rp = ReservoirProfiles(case_id="CaseA", points=[
        ReservoirPoint(t=date(2026,1,1), oil_rate=10_000, gas_rate=15_000, water_rate=2_000, cum_oil=0, cum_gas=0),
        ReservoirPoint(t=date(2026,2,1), oil_rate=9_500, gas_rate=15_500, water_rate=2_100, cum_oil=9_500, cum_gas=15_500),
    ])
    rp_id = svc.register("reservoir_profiles", rp.model_dump())
    svc.approve(rp_id)  # baseline approved → downstream artifacts (wells, engineering, ...) will become stale on their next baseline

    fl = FacilityLoads(points=[
        FacilityLoadsPoint(t=date(2026,1,1), gas_mmscfd=120, oil_kbopd=10, water_kbwpd=2, export_spec="sales"),
        FacilityLoadsPoint(t=date(2026,2,1), gas_mmscfd=122, oil_kbopd=9.5, water_kbwpd=2.1, export_spec="sales"),
    ])
    fl_id = svc.register("facility_loads", fl.model_dump())
    svc.approve(fl_id)

    # 2) Engineering sizes equipment from loads
    es = EquipmentSizingList(items=[
        EquipmentSizingItem(tag="K-1001", service="Gas Compression", type="Compressor", duty_or_size="42 MW", material="CS"),
        EquipmentSizingItem(tag="V-1101", service="Three-Phase Separator", type="Separator", duty_or_size="3 x 100%", material="SS"),
    ])
    es_id = svc.register("equipment_sizing_list", es.model_dump(), upstream_ids=[rp_id, fl_id])
    svc.approve(es_id)

    # 3) LLI identified
    lli = LLICandidates(items=[
        LLICandidate(tag="K-1001", lead_time_days=294, vendor_pool=["Nuovo","MHI"], criticality="high"),
    ])
    lli_id = svc.register("LLI_candidates", lli.model_dump(), upstream_ids=[es_id])
    svc.approve(lli_id)

    # 4) Schedule creates initial install tasks (bare example)
    wbs = WBSActivities(activities=[
        WBSActivity(id="A100", name="Install Compressor K-1001", start=date(2027,1,10), finish=date(2027,4,30), duration=110, logic={"FS":[]}, discipline="Mechanical"),
    ])
    wbs_id = svc.register("wbs_activities", wbs.model_dump(), upstream_ids=[es_id, lli_id])
    svc.approve(wbs_id)

    # 5) Change upstream: Subsurface revises profiles → after approval, downstream marked stale
    rp2 = ReservoirProfiles(case_id="CaseA", points=[
        ReservoirPoint(t=date(2026,1,1), oil_rate=11_500, gas_rate=16_000, water_rate=2_050, cum_oil=0, cum_gas=0),
    ])
    svc.update(rp_id, rp2.model_dump())        # new version pending
    svc.approve(rp_id, as_baseline=True)       # approving new baseline triggers staleness propagation

    # Inspect a downstream artifact state
    latest_wbs = svc.latest("wbs_activities")
    print("WBS stale?", latest_wbs.stale)  # → True
