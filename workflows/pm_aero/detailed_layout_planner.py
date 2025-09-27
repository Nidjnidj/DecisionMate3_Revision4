# workflows/pm_aero/detailed_layout_planner.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Detailed Layout Planner",
    fel_stage="fel3",
    fields=[("layout_version", "CDR-0", "text")],
)