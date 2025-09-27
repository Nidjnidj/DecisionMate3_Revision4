# workflows/pm_gov/risk_register.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Risk Register (quantified)",
    fel_stage="fel3",
    fields=[("p95_cost_musd", 30.0, "float"), ("p50_cost_musd", 24.0, "float")],
)