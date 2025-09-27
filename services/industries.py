from typing import Dict

INDUSTRY_PACKS: Dict[str, Dict[str, str]] = {
    "oil_gas": {
        "pm_module":  "workflows.pm_hub_oil_gas",
        "ops_module": "workflows.ops_hub_oil_gas",
        "projects":   "workflows.workspace_oil_gas",
        "ops_entry":  "render",   # FIXED (was run)
    },
    "construction": {
        "pm_module":  "workflows.pm_hub_construction",
        "ops_module": "workflows.ops_hub_construction",
        "projects":   "workflows.workspace_construction",
        "ops_entry":  "render",
    },
    "green_energy": {
        "pm_module":  "workflows.pm_hub_green_energy",
        "ops_module": "workflows.ops_hub_green_energy",
        "projects":   "workflows.workspace_green_energy",
        "ops_entry":  "render",
    },
    "it": {
        "pm_module":  "workflows.pm_hub_it",
        "ops_module": "workflows.ops_hub_it",
        "projects":   "workflows.workspace_it",
        "ops_entry":  "render",
    },
    "healthcare": {
        "pm_module":  "workflows.pm_hub_healthcare",
        "ops_module": "workflows.ops_hub_healthcare",
        "projects":   "workflows.workspace_healthcare",
        "ops_entry":  "render",
    },
    "government_infrastructure": {
        "pm_module":  "workflows.pm_hub_government_infrastructure",
        "ops_module": "workflows.ops_hub_government_infrastructure",
        "projects":   "workflows.workspace_government_infrastructure",
        "ops_entry":  "render",
    },
    "aerospace_defense": {
        "pm_module":  "workflows.pm_hub_aerospace_defense",
        "ops_module": "workflows.ops_hub_aerospace_defense",
        "projects":   "workflows.workspace_aerospace_defense",
        "ops_entry":  "render",
    },
    "arch_construction": {
        "pm_module":  "workflows.pm_hub_arch_construction",
        "ops_module": "workflows.ops_hub_arch_construction",
        "projects":   "workflows.workspace_arch_construction",
        "ops_entry":  "render",   # FIXED key name
    },
}

def route(industry: str, kind: str):
    pack = INDUSTRY_PACKS.get(industry)
    if not pack:
        raise KeyError(f"Unknown industry: {industry}")

    if kind in ("pm", "pm_hub"):
        return (pack["pm_module"], "render")
    if kind in ("ops", "ops_hub"):
        return (pack["ops_module"], pack.get("ops_entry", "render"))
    if kind in ("projects", "workspace"):
        return (pack["projects"], "render")
    raise KeyError(f"Unknown kind: {kind}")
