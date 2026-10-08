"""Config flow for Turnov Třídí integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import TurnovTridiApi, TurnovTridiConnectionError, TurnovTridiParseError
from .const import CONF_STREET, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STREET): str,
    }
)


async def validate_input(hass: HomeAssistant, street: str) -> dict[str, Any]:
    """Validate the street by making a test API call."""
    api = TurnovTridiApi(async_get_clientsession(hass), street)

    try:
        result = await api.async_get_schedule(dt_util.now().date())
    except TurnovTridiConnectionError as err:
        raise CannotConnect from err
    except TurnovTridiParseError as err:
        raise NoDataFound from err

    # Check if any data was returned
    if not any(result.values()):
        raise NoDataFound

    return {"title": f"Turnov – {street}"}


def _normalize_street(street: str) -> str:
    """Collapse surrounding and repeated whitespace in a street name."""
    return " ".join(street.split())


class TurnovTridiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Turnov Třídí."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            street = _normalize_street(user_input[CONF_STREET])

            # Check if this street is already configured
            await self.async_set_unique_id(street.lower())
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, street)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoDataFound:
                errors[CONF_STREET] = "no_data"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"], data={CONF_STREET: street}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the street of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            street = _normalize_street(user_input[CONF_STREET])
            unique_id = street.lower()

            if any(
                other.unique_id == unique_id and other.entry_id != entry.entry_id
                for other in self._async_current_entries(include_ignore=False)
            ):
                return self.async_abort(reason="already_configured")

            try:
                info = await validate_input(self.hass, street)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoDataFound:
                errors[CONF_STREET] = "no_data"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=info["title"],
                    data_updates={CONF_STREET: street},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class NoDataFound(HomeAssistantError):
    """Error to indicate no collection data was found for the street."""
