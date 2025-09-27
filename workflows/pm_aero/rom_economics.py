# workflows/pm_aero/rom_economics.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="ROM Economics",
    fel_stage="fel2",
    fields=[("capex_rom_musd", 120.0, "float"), ("opex_rom_musdpy", 15.0, "float")],
)