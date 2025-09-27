# workflows/pm_gov/high_level_cba.py
from workflows.pm_common.stub_tool import make_run
# FEL1 saves → used by FEL2 CONOPS/ROM
run = make_run(
    tool_title="High-level CBA",
    fel_stage="fel1",
    fields=[("demand", 10000, "int"), ("shortlisted_option", "A", "text")],
)