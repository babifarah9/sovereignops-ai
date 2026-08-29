"""Tests for the event-ingestion serving surface."""

from app.fast_api_app import app


def test_pubsub_trigger_route_is_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/apps/{app_name}/trigger/pubsub" in paths
