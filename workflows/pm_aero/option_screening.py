# workflows/pm_aero/option_screening.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Option Screening",
    fel_stage="fel1",
    fields=[("new_line_score", 7, "int"), ("mro_conv_score", 6, "int"), ("notes", "", "text")],
)