# workflows/pm_gov/procurement_strategy.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Procurement Strategy (Outline)",
    fel_stage="fel2",
    fields=[("route", "Open Tender", "text")],
)