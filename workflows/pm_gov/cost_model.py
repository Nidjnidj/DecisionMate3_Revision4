# workflows/pm_gov/cost_model.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Cost Model (CAPEX/OPEX)",
    fel_stage="fel3",
    loads_from="fel2",
    compute=lambda pre: {"capex_musd": round(pre.get("rom_cost_musd", 20.0) * 1.15, 1), "opex_musdpy": 2.5},
)