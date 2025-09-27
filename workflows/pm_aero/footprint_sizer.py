# workflows/pm_aero/footprint_sizer.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Footprint Sizer",
    fel_stage="fel3",
    loads_from="fel2",
    compute=lambda pre: {
        # crude footprint = stations * 200 m2
        "stations": pre.get("stations", 6),
        "takt": pre.get("takt", 60.0),
        "footprint_m2": int(pre.get("stations", 6) * 200),
    },
)