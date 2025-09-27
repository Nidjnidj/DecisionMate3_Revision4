from .subsurface import run as run_subsurface
from .engineering import run as run_engineering
from .schedule import run as run_schedule
from .cost import run as run_cost
from .risk import run as run_risk

from .process_flow_simulation import run as run_pfs_legacy   # your last-rev file

REGISTRY = {
    "Subsurface": run_subsurface,
    "Engineering": run_engineering,
    "Schedule": run_schedule,
    "Cost": run_cost,
    "Risk": run_risk,
    "Process Flow Simulation (Legacy)": run_pfs_legacy,
}
