"""Tests for the Turnov Třídí config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.turnov_tridi.api import (
    TurnovTridiConnectionError,
    TurnovTridiParseError,
)
from custom_components.turnov_tridi.const import CONF_STREET, DOMAIN


async def test_user_flow(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """The street is normalized and stored."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STREET: "  5.   května "}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Turnov – 5. května"
    assert result["data"] == {CONF_STREET: "5. května"}
    assert result["result"].unique_id == "5. května"


@pytest.mark.parametrize(
    ("side_effect", "schedule", "errors"),
    [
        (TurnovTridiConnectionError, None, {"base": "cannot_connect"}),
        (TurnovTridiParseError, None, {CONF_STREET: "no_data"}),
        (None, {"mixed_waste": [], "plastic": []}, {CONF_STREET: "no_data"}),
        (RuntimeError, None, {"base": "unknown"}),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_api: AsyncMock,
    side_effect: type[Exception] | None,
    schedule: dict | None,
    errors: dict[str, str],
) -> None:
    """Errors are shown on the form and the flow can recover."""
    working_schedule = mock_api.async_get_schedule.return_value
    mock_api.async_get_schedule.side_effect = side_effect
    if schedule is not None:
        mock_api.async_get_schedule.return_value = schedule

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STREET: "Károvsko"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    mock_api.async_get_schedule.side_effect = None
    mock_api.async_get_schedule.return_value = working_schedule
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STREET: "Károvsko"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_api: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The same street cannot be added twice."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STREET: " KÁROVSKO "}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure_flow(
    hass: HomeAssistant, mock_api: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """The street of an existing entry can be changed."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STREET: "Bezručova"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data == {CONF_STREET: "Bezručova"}
    assert config_entry.unique_id == "bezručova"
    assert config_entry.title == "Turnov – Bezručova"


async def test_reconfigure_flow_already_configured(
    hass: HomeAssistant, mock_api: AsyncMock, config_entry: MockConfigEntry
) -> None:
    """Reconfiguring to a street of another entry is refused."""
    config_entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN, unique_id="bezručova", data={CONF_STREET: "Bezručova"}
    ).add_to_hass(hass)

    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STREET: "Bezručova"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert config_entry.data == {CONF_STREET: "Károvsko"}
