# workflows/pm_aero/site_capability_screener.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Site / Capability Screener",
    fel_stage="fel1",
    fields=[("sites_considered", 3, "int"), ("preferred_site", "Site A", "text")],
)