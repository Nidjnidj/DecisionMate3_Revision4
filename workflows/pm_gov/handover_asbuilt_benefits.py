# workflows/pm_gov/handover_asbuilt_benefits.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Handover / As-built & Benefits",
    fel_stage="fel4",
    fields=[("asbuilt_pkg", "v1", "text"), ("benefits_tracking", True, "text")],
)