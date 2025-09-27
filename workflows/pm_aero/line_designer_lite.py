# workflows/pm_aero/line_designer_lite.py
from workflows.pm_common.stub_tool import make_run

# Load FEL1 → compute stations & takt → save FEL2
run = make_run(
    tool_title="Line Designer (Lite)",
    fel_stage="fel2",
    loads_from="fel1",
    compute=lambda pre: {
        # assume 220 working days, 2 shifts, 7h net per shift, WIP=stations
        "stations": max(1, int((pre.get("annual_aircraft", 60) / 220) / 0.5)),
        "takt": round( (2 * 7 * 60) / max(1, int((pre.get("annual_aircraft", 60) / 220) / 0.5)), 1),  # minutes/station
    },
)