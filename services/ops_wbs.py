# services/ops_wbs.py
from __future__ import annotations
from typing import Dict, List, Any
import streamlit as st
from data.firestore import load_project_doc, save_project_doc

# ---- Templates you can tweak anytime ----
TASK_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "daily_ops": {
        "Operations": [
            "Log daily production",
            "Verify uptime target met",
            "Record incidents / near-misses",
        ],
        "Maintenance": [
            "PM work orders closed",
            "Critical spares review",
        ],
        "HSE": [
            "Toolbox talk completed",
            "Permit to Work audit",
        ],
    },
    "small_projects": {
        "Initiation": [
            "Problem statement approved",
            "Sponsor identified",
        ],
        "Design": [
            "Scope & drawings (L3)",
            "Cost & schedule baseline",
            "Risk register drafted",
        ],
        "Execution": [
            "Materials/procurement issued",
            "Construction start",
            "QA/QC checkpoints",
        ],
        "Closeout": [
            "Commissioning complete",
            "As-built docs filed",
            "Lessons learned captured",
        ],
    },
}

def doc_key(ops_mode: str) -> str:
    return f"ops_tasks_{ops_mode}"

def load_ops_tasks(username: str, namespace: str, project_id: str, ops_mode: str) -> Dict[str, Any]:
    dk = doc_key(ops_mode)
    return load_project_doc(username, namespace, project_id, dk) or {"checked": []}

def save_ops_tasks(username: str, namespace: str, project_id: str, ops_mode: str, checked: List[str]) -> Dict[str, Any]:
    dk = doc_key(ops_mode)
    return save_project_doc(username, namespace, project_id, dk, {"checked": checked})
