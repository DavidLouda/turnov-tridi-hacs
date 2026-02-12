"""Config flow for Turnov Třídí integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_STREET, DOMAIN
from .coordinator import TurnovTridiCoordinator

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STREET): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input by making a test API call."""
    coordinator = TurnovTridiCoordinator(hass, data[CONF_STREET])

    try:
        result = await coordinator._fetch_data()
    except aiohttp.ClientError as err:
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation")
        raise CannotConnect from err

    # Check if any data was returned
    total_events = sum(len(v) for v in result.values())
    if total_events == 0:
        raise NoDataFound

    return {"title": f"Turnov – {data[CONF_STREET]}"}


class TurnovTridiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Turnov Třídí."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if this street is already configured
            await self.async_set_unique_id(user_input[CONF_STREET].lower().strip())
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoDataFound:
                errors[CONF_STREET] = "no_data"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class NoDataFound(HomeAssistantError):
    """Error to indicate no collection data was found for the street."""
