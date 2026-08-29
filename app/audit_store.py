"""Firestore-backed incident and audit persistence for SovereignOps."""

from __future__ import annotations

import copy
import functools
import hashlib
import os
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from google.cloud import firestore

DEFAULT_COLLECTION = "incidents"
DEFAULT_RECEIPT_COLLECTION = "event_receipts"


class ClaimResult(StrEnum):
    """Outcome of atomically claiming an event for processing."""

    CLAIMED = "claimed"
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@functools.cache
def get_firestore_client() -> firestore.Client:
    """Return a process-wide Firestore client using application credentials."""
    return firestore.Client(
        project=os.getenv("GOOGLE_CLOUD_PROJECT") or None,
        database=os.getenv("FIRESTORE_DATABASE", "(default)"),
    )


def _receipt_ref(event_key: str):
    collection = os.getenv(
        "FIRESTORE_EVENT_RECEIPT_COLLECTION", DEFAULT_RECEIPT_COLLECTION
    )
    receipt_id = hashlib.sha256(event_key.encode()).hexdigest()
    return get_firestore_client().collection(collection).document(receipt_id)


def claim_event(
    event_key: str,
    *,
    message_id: str | None,
    incident_id: str | None,
    lease_seconds: int = 600,
) -> ClaimResult:
    """Atomically claim an event, suppressing completed or concurrent duplicates."""
    client = get_firestore_client()
    receipt_ref = _receipt_ref(event_key)
    transaction = client.transaction()
    now = _utc_now()

    @firestore.transactional
    def claim(transaction):
        snapshot = receipt_ref.get(transaction=transaction)
        existing = snapshot.to_dict() if snapshot.exists else {}
        status = existing.get("status")
        lease_until = existing.get("lease_until")

        if status == "COMPLETED":
            return ClaimResult.COMPLETED
        if status == "PROCESSING" and lease_until and lease_until > now:
            return ClaimResult.IN_PROGRESS

        transaction.set(
            receipt_ref,
            {
                "event_key": event_key,
                "message_id": message_id,
                "incident_id": incident_id,
                "status": "PROCESSING",
                "attempt_count": int(existing.get("attempt_count", 0)) + 1,
                "claimed_at": now,
                "lease_until": datetime.fromtimestamp(
                    now.timestamp() + lease_seconds, tz=UTC
                ),
                "updated_at": now,
            },
        )
        return ClaimResult.CLAIMED

    return claim(transaction)


def complete_event(event_key: str) -> None:
    """Mark a successfully processed event as permanently complete."""
    now = _utc_now()
    _receipt_ref(event_key).set(
        {
            "status": "COMPLETED",
            "completed_at": now,
            "updated_at": now,
        },
        merge=True,
    )


def release_event(event_key: str, error: str) -> None:
    """Release a failed claim so a later Pub/Sub delivery may retry it."""
    now = _utc_now()
    _receipt_ref(event_key).set(
        {
            "status": "FAILED",
            "last_error": error[:1000],
            "lease_until": now,
            "updated_at": now,
        },
        merge=True,
    )


def record_audit_event(
    incident_id: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    status: str | None = None,
) -> str:
    """Persist an immutable audit event and update the incident summary."""
    timestamp = _utc_now()
    event_id = f"{timestamp:%Y%m%dT%H%M%S%fZ}-{uuid4().hex[:8]}"
    collection = os.getenv("FIRESTORE_INCIDENT_COLLECTION", DEFAULT_COLLECTION)
    incident_ref = get_firestore_client().collection(collection).document(incident_id)

    event = {
        "event_id": event_id,
        "incident_id": incident_id,
        "event_type": event_type,
        "payload": copy.deepcopy(payload),
        "recorded_at": timestamp,
    }
    incident_ref.collection("audit_events").document(event_id).set(event)

    summary: dict[str, Any] = {
        "incident_id": incident_id,
        "last_event_type": event_type,
        "updated_at": timestamp,
    }
    if status is not None:
        summary["status"] = status
    if event_type == "incident_observed":
        summary["initial_telemetry"] = copy.deepcopy(payload)
        summary["created_at"] = timestamp
    if event_type == "verification_completed":
        summary["final_verification"] = copy.deepcopy(payload)

    incident_ref.set(summary, merge=True)
    return event_id
