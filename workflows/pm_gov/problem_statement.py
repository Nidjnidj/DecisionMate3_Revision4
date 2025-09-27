# workflows/pm_gov/problem_statement.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Problem / Needs Statement",
    fel_stage="fel1",
    fields=[("problem", "", "text"), ("benefits", "", "text")],
)