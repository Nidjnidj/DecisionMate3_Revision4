# workflows/pm_aero/opex_model.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="OPEX Model",
    fel_stage="fel3",
    loads_from="fel2",
    compute=lambda pre: {"opex_est_musdpy": round( pre.get("stations", 6) * 1.8, 1)},
)