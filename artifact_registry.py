# artifact_registry.py
from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
from google.cloud.firestore_v1 import FieldFilter

try:
    import firebase_admin
    from firebase_admin import firestore
except Exception:
    firebase_admin = None
    firestore = None

# === Firestore helpers ===

def _get_db():
    if firebase_admin and firebase_admin._apps:
        return firestore.client()
    return None

# In-memory fallback so the app still runs without Firebase
_INMEMORY = {
    "artifacts": [],
    "events": [],
    "baselines": [],
}

# === Core API ===

def save_artifact(project_id: str, phase_id: str, workstream: str, a_type: str, data: Dict[str, Any],
                  status: str = "Draft", sources: Optional[List[str]] = None, tags: Optional[List[str]] = None,
                  created_by: str = "system") -> Dict[str, Any]:
    now = int(time.time())
    payload = {
        "artifact_id": f"A-{now}",
        "project_id": project_id,
        "phase_id": phase_id,
        "workstream": workstream,
        "type": a_type,
        "version": 1,
        "status": status,
        "data": data,
        "sources": sources or [],
        "notes": "",
        "tags": tags or [],
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    db = _get_db()
    if db:
        doc_ref = db.collection("projects").document(project_id).collection("artifacts").document()
        payload["artifact_id"] = doc_ref.id
        doc_ref.set(payload)
    else:
        _mem()["artifacts"].append(payload)

    # always emit a lightweight created event (optional)
    publish_event(project_id, "artifact.created", {
        "artifact_id": payload["artifact_id"],
        "type": a_type,
        "phase_id": phase_id,
        "workstream": workstream,
    })

    # IMPORTANT: if saved as Approved, emit the approval event too,
    # so downstream handlers (Engineering→Schedule→Finance) run.
    if status == "Approved":
        publish_event(project_id, "artifact.approved", {
            "artifact_id": payload["artifact_id"],
            "type": a_type,
            "phase_id": phase_id,
            "workstream": workstream,
        })

    return payload



def approve_artifact(project_id: str, artifact_id: str) -> Optional[Dict[str, Any]]:
    now = int(time.time())
    db = _get_db()
    if db:
        arts = (
            db.collection("projects")
              .document(project_id)
              .collection("artifacts")
              .where(filter=FieldFilter("artifact_id", "==", artifact_id))
              .stream()
        )

        doc = None
        for d in arts:
            doc = d
            break
        if not doc:
            return None
        data = doc.to_dict()
        data["status"] = "Approved"
        data["version"] = int(data.get("version", 1)) + 1
        data["updated_at"] = now
        db.collection("projects").document(project_id).collection("artifacts").document(doc.id).set(data)
        publish_event(project_id, "artifact.approved", {"artifact_id": data["artifact_id"], "type": data["type"], "phase_id": data["phase_id"], "workstream": data["workstream"]})
        return data
    # in-memory
    for i, a in enumerate(_INMEMORY["artifacts"]):
        if a["artifact_id"] == artifact_id and a["project_id"] == project_id:
            a = dict(a)
            a["status"] = "Approved"
            a["version"] = int(a.get("version", 1)) + 1
            a["updated_at"] = now
            _INMEMORY["artifacts"][i] = a
            publish_event(project_id, "artifact.approved", {"artifact_id": a["artifact_id"], "type": a["type"], "phase_id": a["phase_id"], "workstream": a["workstream"]})
            return a
    return None


# 🔧 HOTFIX: avoid composite-index requirement by sorting client-side
# (Equality filters are fine with single-field indexes; we drop order_by and sort in Python.)

def get_latest(project_id: str, a_type: str, phase_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if db:
        q = (
            db.collection("projects")
            .document(project_id)
            .collection("artifacts")
            .where(filter=FieldFilter("type", "==", a_type))
        )

        if phase_id:
            q = q.where(filter=FieldFilter("phase_id", "==", phase_id))

        docs = list(q.stream())  # no order_by -> no composite index required
        items = [d.to_dict() for d in docs]
        if not items:
            return None
        return max(items, key=lambda x: x.get("updated_at", 0))
    # in-memory
    candidates = [a for a in _INMEMORY["artifacts"] if a["project_id"] == project_id and a["type"] == a_type and (phase_id is None or a["phase_id"] == phase_id)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda x: x.get("updated_at", 0), reverse=True)[0]


def list_required_artifacts(phase_code: str) -> List[Dict[str, str]]:
    # Minimal mapping from Section 3
    mapping = {
        "FEL1": [
            {"workstream": "Subsurface",  "type": "Reservoir_Profiles"},
            {"workstream": "Engineering", "type": "Reference_Case_Identification"},
            {"workstream": "Schedule",    "type": "WBS"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Procurement", "type": "Long_Lead_List"},
            {"workstream": "Finance",     "type": "Cost_Model"},
            {"workstream": "Risk",        "type": "Risk_Register"},
        ],
        "FEL2": [
            {"workstream": "Subsurface",  "type": "Reservoir_Profiles"},
            {"workstream": "Engineering", "type": "Concept_Selected"},
            {"workstream": "Schedule",    "type": "WBS"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Procurement", "type": "Long_Lead_List"},
            {"workstream": "Finance",     "type": "Cost_Model"},
            {"workstream": "Risk",        "type": "Risk_Register"},
        ],
        "FEL3": [
            {"workstream": "Subsurface",  "type": "Reservoir_Profiles"},
            {"workstream": "Engineering", "type": "Defined_Concept"},
            {"workstream": "Schedule",    "type": "WBS"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Procurement", "type": "Long_Lead_List"},
            {"workstream": "Finance",     "type": "Cost_Model"},
            {"workstream": "Risk",        "type": "Risk_Register"},
        ],
        "FEL4": [
            {"workstream": "Subsurface",  "type": "Reservoir_Profiles"},
            {"workstream": "Engineering", "type": "Execution_Concept"},
            {"workstream": "Schedule",    "type": "WBS"},
            {"workstream": "Schedule",    "type": "Schedule_Network"},
            {"workstream": "Procurement", "type": "Long_Lead_List"},
            {"workstream": "Finance",     "type": "Cost_Model"},
            {"workstream": "Risk",        "type": "Risk_Register"},
        ],
        # Example ops mapping remains
        "OPS_DAILY": [
            {"workstream": "Operations",  "type": "Reservoir_Profiles"},
            {"workstream": "Maintenance", "type": "Schedule_Network"},
            {"workstream": "Risk",        "type": "Risk_Register"},
            {"workstream": "Finance",     "type": "Cost_Model"},
        ],
    }

    return mapping.get(phase_code, [])

# === Events ===

def publish_event(project_id: str, event_type: str, payload: Dict[str, Any]):
    db = _get_db()
    event = {
        "project_id": project_id,
        "event_type": event_type,
        "payload": payload,
        "ts": int(time.time()),
    }
    if db:
        db.collection("projects").document(project_id).collection("events").add(event)
    else:
        _INMEMORY["events"].append(event)


def read_events(project_id: str, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _get_db()
    if db:
        q = db.collection("projects").document(project_id).collection("events").order_by("ts", direction=firestore.Query.DESCENDING).limit(100)
        docs = list(q.stream())
        items = [d.to_dict() for d in docs]
        return [e for e in items if not event_type or e.get("event_type") == event_type]
    return [e for e in reversed(_INMEMORY["events"]) if e["project_id"] == project_id and (not event_type or e["event_type"] == event_type)]