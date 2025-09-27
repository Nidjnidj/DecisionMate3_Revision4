# workflows/pm_aero/throughput_sim_lite.py
from workflows.pm_common.stub_tool import make_run
run = make_run(
    tool_title="Throughput Simulator (Lite)",
    fel_stage="fel2",
    fields=[("buffer_wip", 3, "int"), ("uptime", 0.9, "float")],
)