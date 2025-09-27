# services/mappers.py
from typing import Tuple

# services/mappers.py
# services/mappers.py
def route(industry: str, mode: str):
    industry = (industry or "").lower()
    mode = (mode or "").lower()

    if mode == "ops":
        if industry == "healthcare":
            return ("workflows.ops_hub_healthcare", "render")
        if industry == "construction":
            return ("workflows.ops_hub_construction", "render")
        if industry == "green_energy":
            return ("workflows.ops_hub_green_energy", "render")
        if industry == "it":
            return ("workflows.ops_hub_it", "render")
        return ("workflows.ops_hub_oil_gas", "render")  # default

    # PM (projects) hubs
    if industry == "healthcare":
        return ("workflows.pm_hub_healthcare", "render")
    if industry == "construction":
        return ("workflows.pm_hub_construction", "render")
    if industry in ("green_energy", "it"):
        return ("workflows.pm_hub_oil_gas", "render")  # temporary fallback
    return ("workflows.pm_hub_oil_gas", "render")
