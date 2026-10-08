"""Fixtures for Turnov Třídí tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.turnov_tridi.const import CONF_STREET, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the integration from custom_components."""


@pytest.fixture(autouse=True)
def mock_frontend() -> Generator[None]:
    """Skip serving the Lovelace card, the test hass has no frontend or http."""
    with (
        patch(
            "homeassistant.loader.Integration.dependencies",
            new_callable=lambda: property(
                lambda self: (
                    []
                    if self.domain == DOMAIN
                    else self.manifest.get("dependencies", [])
                )
            ),
        ),
        patch("custom_components.turnov_tridi.async_setup", return_value=True),
    ):
        yield


SCHEDULE = {
    "mixed_waste": [date(2026, 3, 10), date(2026, 3, 24)],
    "plastic": [date(2026, 3, 11), date(2026, 3, 25)],
    "paper": [date(2026, 3, 11)],
    "bio_waste": [],
}


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Mock the turnovtridi.cz API client."""
    with (
        patch(
            "custom_components.turnov_tridi.TurnovTridiApi", autospec=True
        ) as api_cls,
        patch(
            "custom_components.turnov_tridi.config_flow.TurnovTridiApi",
            new=api_cls,
        ),
    ):
        api = api_cls.return_value
        api.async_get_schedule.return_value = {k: list(v) for k, v in SCHEDULE.items()}
        yield api


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a config entry for the street Károvsko."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Turnov – Károvsko",
        unique_id="károvsko",
        data={CONF_STREET: "Károvsko"},
    )
