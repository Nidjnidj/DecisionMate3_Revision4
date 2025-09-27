# workflows/pm_gov/rom_economics.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="ROM Economics",
    fel_stage="fel2",
    loads_from="fel1",
    compute=lambda pre: {"rom_npv_musd": round( pre.get("demand", 10000) * 0.0005, 2)},
)