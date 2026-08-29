"""Unit tests for Pub/Sub idempotency handling."""

import base64
import json

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import event_ingestion
from app.audit_store import ClaimResult


def pubsub_envelope(payload: dict, message_id: str = "message-1") -> dict:
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    return {
        "message": {"data": data, "messageId": message_id},
        "subscription": "projects/test/subscriptions/incident-events",
    }


def test_extract_event_identity_prefers_explicit_event_id() -> None:
    identity = event_ingestion.extract_event_identity(
        pubsub_envelope(
            {"event_id": "EVT-001", "incident_id": "INC-5G-001"},
            message_id="message-1",
        )
    )

    assert identity is not None
    assert identity.event_key == "EVT-001"
    assert identity.incident_id == "INC-5G-001"
    assert identity.message_id == "message-1"


def test_duplicate_completed_event_is_acknowledged_without_processing(
    monkeypatch,
) -> None:
    app = FastAPI()
    processed: list[dict] = []

    @app.post("/apps/app/trigger/pubsub")
    async def trigger(request: Request):
        processed.append(await request.json())
        return {"status": "processed"}

    app.middleware("http")(event_ingestion.enforce_pubsub_idempotency)
    monkeypatch.setattr(
        event_ingestion,
        "claim_event",
        lambda *args, **kwargs: ClaimResult.COMPLETED,
    )

    response = TestClient(app).post(
        "/apps/app/trigger/pubsub",
        json=pubsub_envelope({"incident_id": "INC-5G-001"}),
    )

    assert response.status_code == 204
    assert processed == []


def test_successful_event_is_completed_and_subscription_is_normalized(
    monkeypatch,
) -> None:
    app = FastAPI()
    processed: list[dict] = []
    completed: list[str] = []

    @app.post("/apps/app/trigger/pubsub")
    async def trigger(request: Request):
        processed.append(await request.json())
        return {"status": "processed"}

    app.middleware("http")(event_ingestion.enforce_pubsub_idempotency)
    monkeypatch.setattr(
        event_ingestion,
        "claim_event",
        lambda *args, **kwargs: ClaimResult.CLAIMED,
    )
    monkeypatch.setattr(event_ingestion, "complete_event", completed.append)

    response = TestClient(app).post(
        "/apps/app/trigger/pubsub",
        json=pubsub_envelope({"incident_id": "INC-5G-001"}),
    )

    assert response.status_code == 200
    assert completed == ["INC-5G-001"]
    assert processed[0]["subscription"] == "incident-events"
