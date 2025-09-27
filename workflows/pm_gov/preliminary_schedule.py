# workflows/pm_gov/preliminary_schedule.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Preliminary Schedule",
    fel_stage="fel2",
    fields=[("duration_months", 18, "int"), ("critical_path", "Design→Procure→Build", "text")],
)