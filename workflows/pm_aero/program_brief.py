# workflows/pm_aero/program_brief.py
from workflows.pm_common.stub_tool import make_run

# FEL1 saves → used by FEL2.Line Designer
run = make_run(
    tool_title="Program Brief",
    fel_stage="fel1",
    fields=[
        ("annual_aircraft", 60, "int"),
        ("mix", 0.7, "float"),  # narrowbody share (0..1)
        ("avg_price", 85_000_000, "float"),
    ],
)