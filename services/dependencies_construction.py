
DAG = {
    "design_package": {"downstream": ["master_schedule", "procurement_plan"]},
    "master_schedule": {"downstream": ["construction_wbs"]},
    "procurement_plan": {"downstream": ["construction_wbs"]},
    "construction_wbs": {"downstream": []},
}
PRODUCER = {
    "design_package": "engineering",
    "master_schedule": "project_controls",
    "procurement_plan": "procurement",
    "construction_wbs": "construction",
}
