# workflows/pm_aero/qualification_readiness.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Qualification & Commissioning Readiness",
    fel_stage="fel4",
    fields=[("readiness_pct", 75, "int")],
)