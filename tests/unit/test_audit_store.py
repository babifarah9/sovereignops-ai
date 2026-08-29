"""Unit tests for Firestore incident persistence."""

from datetime import UTC, datetime, timedelta

from app import audit_store


class FakeDocument:
    def __init__(self) -> None:
        self.writes: list[tuple[dict, bool]] = []
        self.children: dict[str, FakeCollection] = {}
        self.data: dict | None = None

    def collection(self, name: str):
        return self.children.setdefault(name, FakeCollection())

    def set(self, data: dict, merge: bool = False) -> None:
        self.writes.append((data, merge))
        if merge and self.data:
            self.data.update(data)
        else:
            self.data = dict(data)

    def get(self, transaction=None):
        del transaction
        return FakeSnapshot(self.data)


class FakeSnapshot:
    def __init__(self, data: dict | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> dict:
        return dict(self._data or {})


class FakeTransaction:
    def set(self, document: FakeDocument, data: dict) -> None:
        document.set(data)


class FakeCollection:
    def __init__(self) -> None:
        self.documents: dict[str, FakeDocument] = {}

    def document(self, name: str):
        return self.documents.setdefault(name, FakeDocument())


class FakeClient:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def collection(self, name: str):
        return self.collections.setdefault(name, FakeCollection())

    def transaction(self):
        return FakeTransaction()


def test_record_audit_event_writes_event_and_summary(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(audit_store, "get_firestore_client", lambda: client)

    event_id = audit_store.record_audit_event(
        "INC-5G-001",
        "incident_observed",
        {"latency_ms": 184},
        status="ACTIVE",
    )

    incident = client.collections["incidents"].documents["INC-5G-001"]
    event = incident.children["audit_events"].documents[event_id].writes[0][0]
    summary, merge = incident.writes[0]

    assert event["event_type"] == "incident_observed"
    assert event["payload"] == {"latency_ms": 184}
    assert summary["initial_telemetry"] == {"latency_ms": 184}
    assert summary["status"] == "ACTIVE"
    assert merge is True


def test_claim_event_suppresses_completed_event(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(audit_store, "get_firestore_client", lambda: client)
    monkeypatch.setattr(audit_store.firestore, "transactional", lambda func: func)

    first = audit_store.claim_event(
        "INC-5G-001",
        message_id="message-1",
        incident_id="INC-5G-001",
    )
    audit_store.complete_event("INC-5G-001")
    duplicate = audit_store.claim_event(
        "INC-5G-001",
        message_id="message-2",
        incident_id="INC-5G-001",
    )

    assert first == audit_store.ClaimResult.CLAIMED
    assert duplicate == audit_store.ClaimResult.COMPLETED


def test_claim_event_suppresses_active_lease(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(audit_store, "get_firestore_client", lambda: client)
    monkeypatch.setattr(audit_store.firestore, "transactional", lambda func: func)
    monkeypatch.setattr(
        audit_store,
        "_utc_now",
        lambda: datetime(2026, 8, 29, tzinfo=UTC),
    )

    assert (
        audit_store.claim_event(
            "INC-5G-002",
            message_id="message-1",
            incident_id="INC-5G-002",
        )
        == audit_store.ClaimResult.CLAIMED
    )
    receipt = next(iter(client.collections["event_receipts"].documents.values()))
    assert receipt.data["lease_until"] > datetime.now(UTC) - timedelta(days=3650)
    assert (
        audit_store.claim_event(
            "INC-5G-002",
            message_id="message-1",
            incident_id="INC-5G-002",
        )
        == audit_store.ClaimResult.IN_PROGRESS
    )
