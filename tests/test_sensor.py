"""Tests for the Turnov Třídí sensors and calendar."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.turnov_tridi.api import TurnovTridiConnectionError

NEXT = "sensor.svoz_odpadu_karovsko_next_collection"
PLASTIC = "sensor.svoz_odpadu_karovsko_plastic"
BIO = "sensor.svoz_odpadu_karovsko_bio_waste"
CALENDAR = "calendar.svoz_odpadu_karovsko"


async def _setup(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_sensors(
    hass: HomeAssistant,
    mock_api: AsyncMock,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Sensors show the next collection and its countdown."""
    freezer.move_to("2026-03-10 08:00:00+01:00")
    await _setup(hass, config_entry)

    state = hass.states.get(PLASTIC)
    assert state.state == "2026-03-11"
    assert state.attributes["waste_key"] == "plastic"
    assert state.attributes["waste_type"] == "Plasty"
    assert state.attributes["days_until"] == 1
    assert state.attributes["is_tomorrow"] is True
    assert state.attributes["upcoming_dates"] == ["2026-03-11", "2026-03-25"]

    assert hass.states.get(BIO).state == STATE_UNKNOWN

    state = hass.states.get(NEXT)
    assert state.state == "2026-03-10"
    assert state.attributes["waste_type"] == "Směsný komunální odpad"
    assert state.attributes["is_today"] is True
    assert state.attributes["upcoming_summary"] == [
        {"date": "2026-03-10", "waste_type": "Směsný komunální odpad"},
        {"date": "2026-03-11", "waste_type": "Plasty"},
        {"date": "2026-03-11", "waste_type": "Papír"},
    ]


async def test_state_rolls_over_at_midnight(
    hass: HomeAssistant,
    mock_api: AsyncMock,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """At midnight the states move on without waiting for the next refresh."""
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to("2026-03-10 23:59:00+01:00")
    await _setup(hass, config_entry)
    assert hass.states.get(NEXT).state == "2026-03-10"

    freezer.move_to("2026-03-11 00:00:00+01:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(NEXT)
    assert state.state == "2026-03-11"
    assert state.attributes["waste_type"] == "Plasty, Papír"
    assert state.attributes["waste_types"] == ["Plasty", "Papír"]
    assert state.attributes["waste_keys"] == ["plastic", "paper"]
    assert state.attributes["is_today"] is True
    assert hass.states.get(PLASTIC).attributes["is_today"] is True
    # Only one fetch happened; the rollover is computed locally
    assert mock_api.async_get_schedule.await_count == 1


async def test_failed_update_keeps_data(
    hass: HomeAssistant,
    mock_api: AsyncMock,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A failed refresh keeps the last known schedule."""
    freezer.move_to("2026-03-10 08:00:00+01:00")
    await _setup(hass, config_entry)

    mock_api.async_get_schedule.side_effect = TurnovTridiConnectionError
    freezer.tick(timedelta(hours=7))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert mock_api.async_get_schedule.await_count == 2
    assert hass.states.get(PLASTIC).state == "2026-03-11"


async def test_calendar(
    hass: HomeAssistant,
    mock_api: AsyncMock,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The calendar lists every collection as an all-day event."""
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to("2026-03-10 08:00:00+01:00")
    await _setup(hass, config_entry)

    state = hass.states.get(CALENDAR)
    assert state.state == "on"
    assert state.attributes["message"] == "Směsný komunální odpad"
    assert state.attributes["location"] == "Károvsko"

    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": CALENDAR,
            "start_date_time": dt_util.parse_datetime("2026-03-11T00:00:00+01:00"),
            "end_date_time": dt_util.parse_datetime("2026-03-25T00:00:00+01:00"),
        },
        blocking=True,
        return_response=True,
    )
    events = result[CALENDAR]["events"]
    assert [(e["start"], e["summary"]) for e in events] == [
        ("2026-03-11", "Plasty"),
        ("2026-03-11", "Papír"),
        ("2026-03-24", "Směsný komunální odpad"),
    ]


async def test_unload(
    hass: HomeAssistant, mock_api: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The entry unloads cleanly."""
    await _setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(PLASTIC).state == "unavailable"
