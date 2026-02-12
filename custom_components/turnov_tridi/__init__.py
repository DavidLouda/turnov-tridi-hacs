"""The Turnov Třídí integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_STREET, DOMAIN
from .coordinator import TurnovTridiCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Turnov Třídí from a config entry."""
    coordinator = TurnovTridiCoordinator(hass, entry.data[CONF_STREET])

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Copy the Lovelace card to www/ so it can be served
    await hass.async_add_executor_job(_copy_card_resource, hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def _copy_card_resource(hass: HomeAssistant) -> None:
    """Copy the custom Lovelace card JS to the HA www directory."""
    src = Path(__file__).parent / "www" / "turnov-tridi-card.js"
    if not src.exists():
        _LOGGER.warning("Lovelace card file not found: %s", src)
        return

    www_dir = Path(hass.config.path("www")) / "community" / "turnov_tridi"
    www_dir.mkdir(parents=True, exist_ok=True)

    dest = www_dir / "turnov-tridi-card.js"
    if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        _LOGGER.info("Turnov Třídí Lovelace card copied to %s", dest)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
