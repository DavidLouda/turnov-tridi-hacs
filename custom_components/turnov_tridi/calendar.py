"""Calendar platform for Turnov Třídí integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TurnovTridiConfigEntry
from .const import WASTE_TYPES_BY_KEY
from .coordinator import TurnovTridiCoordinator
from .entity import TurnovTridiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TurnovTridiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Turnov Třídí calendar from a config entry."""
    async_add_entities([TurnovTridiCalendar(entry.runtime_data)])


class TurnovTridiCalendar(TurnovTridiEntity, CalendarEntity):
    """Calendar with all upcoming waste collections."""

    _attr_icon = "mdi:delete-variant"
    # Use the device name, e.g. "Svoz odpadu – Károvsko"
    _attr_name = None

    def __init__(self, coordinator: TurnovTridiCoordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, "calendar")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming collection."""
        next_date, waste_keys = self.coordinator.next_collection()
        if next_date is None:
            return None
        return self._event(next_date, waste_keys[0])

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return collections within a datetime range."""
        events = [
            self._event(collection_date, waste_key)
            for waste_key, dates in (self.coordinator.data or {}).items()
            for collection_date in dates
            # An all-day event spans [midnight, next midnight) in local time
            if dt_util.start_of_local_day(collection_date) < end_date
            and dt_util.start_of_local_day(collection_date + timedelta(days=1))
            > start_date
        ]
        return sorted(events, key=lambda event: event.start)

    def _event(self, collection_date: date, waste_key: str) -> CalendarEvent:
        """Build an all-day event for one collection."""
        return CalendarEvent(
            start=collection_date,
            end=collection_date + timedelta(days=1),
            summary=WASTE_TYPES_BY_KEY[waste_key]["name_cs"],
            location=self._street,
            uid=f"{self.coordinator.config_entry.entry_id}_{waste_key}_{collection_date.isoformat()}",
        )
