"""Pub/Sub envelope parsing and idempotent delivery middleware."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response

from app.audit_store import (
    ClaimResult,
    claim_event,
    complete_event,
    release_event,
)


@dataclass(frozen=True)
class EventIdentity:
    """Stable identifiers extracted from a Pub/Sub push envelope."""

    event_key: str
    message_id: str | None
    incident_id: str | None


def _decode_payload(message: dict[str, Any]) -> dict[str, Any]:
    data = message.get("data")
    if not isinstance(data, str) or not data:
        return {}
    try:
        decoded = base64.b64decode(data, validate=True).decode()
    except (ValueError, UnicodeDecodeError):
        decoded = data
    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_event_identity(envelope: dict[str, Any]) -> EventIdentity | None:
    """Choose a business idempotency key, falling back to the Pub/Sub message ID."""
    message = envelope.get("message")
    if not isinstance(message, dict):
        return None

    payload = _decode_payload(message)
    attributes = message.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}

    message_id = message.get("messageId") or message.get("message_id")
    incident_id = payload.get("incident_id") or attributes.get("incident_id")
    explicit_event_id = payload.get("event_id") or attributes.get("event_id")
    event_key = explicit_event_id or incident_id or message_id
    if not isinstance(event_key, str) or not event_key:
        return None

    return EventIdentity(
        event_key=event_key,
        message_id=message_id if isinstance(message_id, str) else None,
        incident_id=incident_id if isinstance(incident_id, str) else None,
    )


async def enforce_pubsub_idempotency(request: Request, call_next):
    """Claim Pub/Sub events before ADK execution and acknowledge duplicates."""
    if request.method != "POST" or not request.url.path.endswith("/trigger/pubsub"):
        return await call_next(request)

    body = await request.body()
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError:
        return await call_next(request)
    if not isinstance(envelope, dict):
        return await call_next(request)

    subscription = envelope.get("subscription", "")
    if isinstance(subscription, str) and "/" in subscription:
        envelope["subscription"] = subscription.rsplit("/", 1)[-1]
        request._body = json.dumps(envelope).encode()

    identity = extract_event_identity(envelope)
    if identity is None:
        return await call_next(request)

    claim = await run_in_threadpool(
        claim_event,
        identity.event_key,
        message_id=identity.message_id,
        incident_id=identity.incident_id,
    )
    if claim in {ClaimResult.COMPLETED, ClaimResult.IN_PROGRESS}:
        return Response(status_code=204)

    try:
        response = await call_next(request)
    except Exception as exc:
        await run_in_threadpool(release_event, identity.event_key, repr(exc))
        raise

    if 200 <= response.status_code < 300:
        await run_in_threadpool(complete_event, identity.event_key)
    else:
        await run_in_threadpool(
            release_event,
            identity.event_key,
            f"HTTP {response.status_code}",
        )
    return response
