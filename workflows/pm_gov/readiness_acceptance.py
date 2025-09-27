# workflows/pm_gov/readiness_acceptance.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Readiness / Acceptance",
    fel_stage="fel4",
    fields=[("readiness_pct", 70, "int")],
)