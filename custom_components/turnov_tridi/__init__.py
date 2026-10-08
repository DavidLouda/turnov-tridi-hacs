"""The Turnov Třídí integration."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import TurnovTridiApi
from .const import CARD_FILENAME, CARD_URL, CONF_STREET, DOMAIN
from .coordinator import TurnovTridiCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type TurnovTridiConfigEntry = ConfigEntry[TurnovTridiCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the Lovelace card and load it in the frontend automatically."""
    integration = await async_get_integration(hass, DOMAIN)
    card_path = Path(__file__).parent / "www" / CARD_FILENAME

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
    )
    # The version query busts the browser cache after an update
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")

    await hass.async_add_executor_job(_remove_legacy_card_copy, hass)
    return True


def _remove_legacy_card_copy(hass: HomeAssistant) -> None:
    """Remove the card copy older versions placed into www/community."""
    legacy_dir = Path(hass.config.path("www")) / "community" / DOMAIN
    legacy_card = legacy_dir / CARD_FILENAME
    if not legacy_card.exists():
        return

    legacy_card.unlink()
    if not any(legacy_dir.iterdir()):
        legacy_dir.rmdir()
    _LOGGER.warning(
        "Removed the old card copy %s. The card is now loaded automatically; "
        "remove the dashboard resource /local/community/%s/%s",
        legacy_card,
        DOMAIN,
        CARD_FILENAME,
    )


async def async_setup_entry(hass: HomeAssistant, entry: TurnovTridiConfigEntry) -> bool:
    """Set up Turnov Třídí from a config entry."""
    api = TurnovTridiApi(async_get_clientsession(hass), entry.data[CONF_STREET])
    coordinator = TurnovTridiCoordinator(hass, entry, api)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    @callback
    def _async_midnight(now: datetime) -> None:
        """Recalculate the next collection and countdown when the day changes."""
        coordinator.async_update_listeners()

    entry.async_on_unload(
        async_track_time_change(hass, _async_midnight, hour=0, minute=0, second=0)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TurnovTridiConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
