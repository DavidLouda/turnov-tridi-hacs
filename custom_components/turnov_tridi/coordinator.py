"""Data update coordinator for Turnov Třídí."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TurnovTridiApi, TurnovTridiError
from .const import DEFAULT_UPDATE_INTERVAL_HOURS, DOMAIN

if TYPE_CHECKING:
    from . import TurnovTridiConfigEntry

_LOGGER = logging.getLogger(__name__)


class TurnovTridiCoordinator(DataUpdateCoordinator[dict[str, list[date]]]):
    """Coordinator to fetch waste collection data from turnovtridi.cz."""

    config_entry: TurnovTridiConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: TurnovTridiConfigEntry,
        api: TurnovTridiApi,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_UPDATE_INTERVAL_HOURS),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, list[date]]:
        """Fetch data from the API.

        Raising UpdateFailed keeps the previously fetched schedule in place.
        """
        try:
            return await self.api.async_get_schedule(dt_util.now().date())
        except TurnovTridiError as err:
            raise UpdateFailed(str(err)) from err

    def upcoming(self, waste_key: str) -> list[date]:
        """Return collection dates from today on for one waste type."""
        if not self.data:
            return []
        today = dt_util.now().date()
        return [d for d in self.data.get(waste_key, []) if d >= today]

    def next_collection(self) -> tuple[date | None, list[str]]:
        """Return the nearest collection date and all waste keys collected that day."""
        nearest: date | None = None
        keys: list[str] = []
        for waste_key in self.data or {}:
            dates = self.upcoming(waste_key)
            if not dates:
                continue
            if nearest is None or dates[0] < nearest:
                nearest, keys = dates[0], [waste_key]
            elif dates[0] == nearest:
                keys.append(waste_key)
        return nearest, keys
