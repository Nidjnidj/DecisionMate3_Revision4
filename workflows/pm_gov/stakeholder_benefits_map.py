# workflows/pm_gov/stakeholder_benefits_map.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Stakeholder & Benefits Map",
    fel_stage="fel1",
    fields=[("stakeholders", "Dept A; Dept B", "text")],
)