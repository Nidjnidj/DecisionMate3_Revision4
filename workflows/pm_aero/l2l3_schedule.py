# workflows/pm_aero/l2l3_schedule.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="L2/L3 Schedule",
    fel_stage="fel3",
    fields=[("milestones", "CDR, FRR", "text")],
)