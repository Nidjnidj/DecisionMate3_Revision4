# workflows/pm_aero/capacity_shift_plan.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Capacity / Shift Plan",
    fel_stage="fel3",
    loads_from="fel2",
    compute=lambda pre: {"shifts": 2, "max_units_per_day": max(1, int(pre.get("stations", 6) / 2))},
)