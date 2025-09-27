# workflows/pm_aero/market_volume_scenarios.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Market / Volume Scenarios",
    fel_stage="fel1",
    fields=[("low", 40, "int"), ("base", 60, "int"), ("high", 90, "int")],
)