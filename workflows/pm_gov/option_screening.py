# workflows/pm_gov/option_screening.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Option Screening",
    fel_stage="fel1",
    fields=[("option_a_score", 7, "int"), ("option_b_score", 5, "int")],
)