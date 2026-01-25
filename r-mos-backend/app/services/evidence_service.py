"""
Evidence bundle service.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import uuid
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evidence import EvidenceBundle, EvidenceItem
from app.schemas.evidence import (
    EvidenceBundleCreate,
    EvidenceBundleResponse,
    EvidenceBundleListItem,
    EvidenceBundleListResponse,
    EvidenceItem as EvidenceItemSchema,
    HashAlgo,
)


def _bundle_manifest(bundle: EvidenceBundleCreate) -> dict:
    items = sorted(
        [
            {
                "evidence_id": item.evidence_id,
                "evidence_type": item.evidence_type,
                "content_uri": item.content_uri,
                "content_hash": item.content_hash,
                "content_hash_algo": item.content_hash_algo,
                "content_mime_type": item.content_mime_type,
                "size_bytes": item.size_bytes,
                "observed_time": _to_naive(item.observed_time).isoformat(),
                "ingest_time": _to_naive(item.ingest_time).isoformat(),
                "human_summary": item.human_summary,
                "machine_code": item.machine_code,
                "machine_tags": item.machine_tags,
            }
            for item in bundle.items
        ],
        key=lambda x: x["evidence_id"],
    )
    return {
        "bundle_type": bundle.bundle_type,
        "observed_time_start": _to_naive(bundle.observed_time_start).isoformat(),
        "observed_time_end": _to_naive(bundle.observed_time_end).isoformat() if bundle.observed_time_end else None,
        "items": items,
    }


def _compute_bundle_hash(bundle: EvidenceBundleCreate) -> str:
    manifest = _bundle_manifest(bundle)
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def _to_naive(value: datetime | None) -> datetime | None:
    if value and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_bundles(self, page: int, size: int) -> EvidenceBundleListResponse:
        count_query = select(func.count()).select_from(EvidenceBundle)
        total = (await self.db.execute(count_query)).scalar() or 0

        query = select(EvidenceBundle).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(query)).scalars().all()

        items = [
            EvidenceBundleListItem(
                evidence_bundle_id=row.id,
                bundle_type=row.bundle_type,
                observed_time_start=row.observed_time_start,
                ingest_time=row.ingest_time,
                is_sealed=row.is_sealed,
            )
            for row in rows
        ]
        pages = (total + size - 1) // size

        return EvidenceBundleListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def create_bundle(self, request: EvidenceBundleCreate) -> EvidenceBundleResponse:
        bundle_id = str(uuid.uuid4())
        bundle_hash = _compute_bundle_hash(request)
        ingest_time = datetime.utcnow()
        sealed_at = ingest_time

        bundle = EvidenceBundle(
            id=bundle_id,
            bundle_type=request.bundle_type.value,
            bundle_hash=bundle_hash,
            bundle_hash_algo=HashAlgo.SHA256.value,
            observed_time_start=_to_naive(request.observed_time_start),
            observed_time_end=_to_naive(request.observed_time_end),
            ingest_time=ingest_time,
            is_sealed=True,
            sealed_at=sealed_at,
            human_summary=request.human_summary,
            machine_tags=request.machine_tags,
        )
        self.db.add(bundle)

        for item in request.items:
            evidence_item = EvidenceItem(
                id=item.evidence_id,
                bundle_id=bundle_id,
                evidence_type=item.evidence_type.value,
                content_uri=item.content_uri,
                content_hash=item.content_hash,
                content_hash_algo=item.content_hash_algo.value,
                content_mime_type=item.content_mime_type,
                size_bytes=item.size_bytes,
                observed_time=_to_naive(item.observed_time),
                ingest_time=_to_naive(item.ingest_time),
                human_summary=item.human_summary,
                machine_code=item.machine_code,
                machine_tags=item.machine_tags,
            )
            self.db.add(evidence_item)

        await self.db.commit()
        await self.db.refresh(bundle)

        return EvidenceBundleResponse(
            evidence_bundle_id=bundle.id,
            bundle_type=bundle.bundle_type,
            bundle_hash=bundle.bundle_hash,
            bundle_hash_algo=bundle.bundle_hash_algo,
            observed_time_start=bundle.observed_time_start,
            observed_time_end=bundle.observed_time_end,
            ingest_time=bundle.ingest_time,
            is_sealed=bundle.is_sealed,
            sealed_at=bundle.sealed_at,
            items=request.items,
            human_summary=bundle.human_summary,
            machine_tags=bundle.machine_tags,
        )

    async def get_bundle(self, bundle_id: str) -> EvidenceBundleResponse | None:
        query = select(EvidenceBundle).options(selectinload(EvidenceBundle.items)).where(EvidenceBundle.id == bundle_id)
        bundle = (await self.db.execute(query)).scalars().first()
        if not bundle:
            return None

        items: List[EvidenceItemSchema] = [
            EvidenceItemSchema(
                evidence_id=item.id,
                evidence_type=item.evidence_type,
                content_uri=item.content_uri,
                content_hash=item.content_hash,
                content_hash_algo=item.content_hash_algo,
                content_mime_type=item.content_mime_type,
                size_bytes=item.size_bytes,
                observed_time=item.observed_time,
                ingest_time=item.ingest_time,
                human_summary=item.human_summary,
                machine_code=item.machine_code,
                machine_tags=item.machine_tags,
            )
            for item in bundle.items
        ]

        return EvidenceBundleResponse(
            evidence_bundle_id=bundle.id,
            bundle_type=bundle.bundle_type,
            bundle_hash=bundle.bundle_hash,
            bundle_hash_algo=bundle.bundle_hash_algo,
            observed_time_start=bundle.observed_time_start,
            observed_time_end=bundle.observed_time_end,
            ingest_time=bundle.ingest_time,
            is_sealed=bundle.is_sealed,
            sealed_at=bundle.sealed_at,
            items=items,
            human_summary=bundle.human_summary,
            machine_tags=bundle.machine_tags,
        )
