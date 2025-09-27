# workflows/pm_gov/detailed_requirements.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Detailed Requirements Baseline",
    fel_stage="fel3",
    loads_from="fel2",
    compute=lambda pre: {"req_count": 120, "baselined": True},
)