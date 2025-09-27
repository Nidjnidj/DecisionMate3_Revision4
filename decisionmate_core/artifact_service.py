# ============================ artifact_service.py ============================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

from .dependencies import DAG, PRODUCER, downstream_of

@dataclass
class ArtifactRecord:
    artifact_id: str
    artifact_type: str  # e.g., "equipment_sizing_list"
    data: Any
    produced_by: str  # discipline
    upstream_ids: List[str] = field(default_factory=list)
    version: int = 1
    approved: bool = False
    baseline_version: Optional[int] = None
    stale: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class Repo:
    """In-memory repo; swap with Firestore later."""
    def __init__(self):
        self.store: Dict[str, ArtifactRecord] = {}
        self.by_type: Dict[str, List[str]] = {}

    def save(self, rec: ArtifactRecord):
        self.store[rec.artifact_id] = rec
        self.by_type.setdefault(rec.artifact_type, []).append(rec.artifact_id)

    def get(self, artifact_id: str) -> ArtifactRecord:
        return self.store[artifact_id]

    def latest_of_type(self, artifact_type: str) -> Optional[ArtifactRecord]:
        ids = self.by_type.get(artifact_type, [])
        if not ids:
            return None
        return sorted((self.store[i] for i in ids), key=lambda r: r.updated_at)[-1]

class ArtifactService:
    def __init__(self, repo: Optional[Repo] = None):
        self.repo = repo or Repo()

    def register(self, artifact_type: str, data: Any, upstream_ids: Optional[List[str]] = None) -> str:
        produced_by = PRODUCER.get(artifact_type)
        if not produced_by:
            raise ValueError(f"Unknown artifact_type: {artifact_type}")
        aid = str(uuid.uuid4())
        rec = ArtifactRecord(
            artifact_id=aid,
            artifact_type=artifact_type,
            data=data,
            produced_by=produced_by,
            upstream_ids=upstream_ids or [],
        )
        self.repo.save(rec)
        return aid

    def approve(self, artifact_id: str, as_baseline: bool = True):
        rec = self.repo.get(artifact_id)
        rec.approved = True
        if as_baseline:
            rec.baseline_version = rec.version
            self._propagate_stale_from(rec)
        rec.updated_at = datetime.utcnow()
        self.repo.save(rec)

    def update(self, artifact_id: str, new_data: Any):
        rec = self.repo.get(artifact_id)
        rec.data = new_data
        rec.version += 1
        rec.approved = False
        rec.updated_at = datetime.utcnow()
        rec.stale = True
        self.repo.save(rec)

    def get(self, artifact_id: str) -> ArtifactRecord:
        return self.repo.get(artifact_id)

    def latest(self, artifact_type: str) -> Optional[ArtifactRecord]:
        return self.repo.latest_of_type(artifact_type)

    def _propagate_stale_from(self, rec: ArtifactRecord):
        producer = rec.produced_by
        impacted = downstream_of(producer)
        for a_id, a in list(self.repo.store.items()):
            if a.produced_by in impacted:
                a.stale = True
                a.approved = False
                a.updated_at = datetime.utcnow()
                self.repo.save(a)