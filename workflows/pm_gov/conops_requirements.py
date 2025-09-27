# workflows/pm_gov/conops_requirements.py
from workflows.pm_common.stub_tool import make_run
# Load FEL1 → derive ROM ballpark → save FEL2
run = make_run(
    tool_title="CONOPS & Requirements (Draft)",
    fel_stage="fel2",
    loads_from="fel1",
    compute=lambda pre: {
        "option": pre.get("shortlisted_option", "A"),
        "rom_cost_musd": round( pre.get("demand", 10000) * 0.002, 1),
    },
)