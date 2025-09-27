# workflows/pm_aero/handover_asbuilt.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Handover / As-built",
    fel_stage="fel4",
    fields=[("asbuilt_pkg", "v1", "text")],
)