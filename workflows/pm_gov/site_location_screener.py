# workflows/pm_gov/site_location_screener.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Site / Location Screener",
    fel_stage="fel1",
    fields=[("locations", 2, "int"), ("preferred_location", "District 1", "text")],
)