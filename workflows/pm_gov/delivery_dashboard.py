# workflows/pm_gov/delivery_dashboard.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Delivery Dashboard",
    fel_stage="fel4",
    fields=[("spi", 1.0, "float"), ("cpi", 1.0, "float")],
)