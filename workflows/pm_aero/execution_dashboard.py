# workflows/pm_aero/execution_dashboard.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Execution Dashboard",
    fel_stage="fel4",
    fields=[("spi", 0.98, "float"), ("cpi", 1.02, "float")],
)