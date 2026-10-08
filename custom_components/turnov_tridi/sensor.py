"""Sensor platform for Turnov Třídí integration."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TurnovTridiConfigEntry
from .const import WASTE_TYPES, WASTE_TYPES_BY_KEY
from .coordinator import TurnovTridiCoordinator
from .entity import TurnovTridiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TurnovTridiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Turnov Třídí sensors from a config entry."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        TurnovTridiWasteSensor(coordinator, waste_info["key"])
        for waste_info in WASTE_TYPES.values()
    ]
    entities.append(TurnovTridiNextCollectionSensor(coordinator))

    async_add_entities(entities)


def _days_attributes(next_date: date | None) -> dict[str, Any]:
    """Return the countdown attributes for a collection date."""
    if next_date is None:
        return {"days_until": None, "is_tomorrow": False, "is_today": False}
    days_until = (next_date - dt_util.now().date()).days
    return {
        "days_until": days_until,
        "is_tomorrow": days_until == 1,
        "is_today": days_until == 0,
    }


class TurnovTridiWasteSensor(TurnovTridiEntity, SensorEntity):
    """Sensor for a specific waste type collection schedule."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: TurnovTridiCoordinator, waste_key: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, waste_key)
        self._waste_key = waste_key
        self._attr_icon = WASTE_TYPES_BY_KEY[waste_key]["icon"]

    @property
    def native_value(self) -> date | None:
        """Return the next collection date for this waste type."""
        upcoming = self.coordinator.upcoming(self._waste_key)
        return upcoming[0] if upcoming else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        upcoming = self.coordinator.upcoming(self._waste_key)
        return {
            "street": self._street,
            "waste_type": WASTE_TYPES_BY_KEY[self._waste_key]["name_cs"],
            "waste_key": self._waste_key,
            **_days_attributes(upcoming[0] if upcoming else None),
            "upcoming_dates": [d.isoformat() for d in upcoming[:5]],
        }


class TurnovTridiNextCollectionSensor(TurnovTridiEntity, SensorEntity):
    """Sensor showing the very next waste collection of any type."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-alert"

    def __init__(self, coordinator: TurnovTridiCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "next_collection")

    @property
    def native_value(self) -> date | None:
        """Return the nearest collection date."""
        next_date, _ = self.coordinator.next_collection()
        return next_date

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        next_date, waste_keys = self.coordinator.next_collection()
        waste_types = [WASTE_TYPES_BY_KEY[key]["name_cs"] for key in waste_keys]

        # The next collection of each waste type, sorted by date
        upcoming_summary = sorted(
            (
                {
                    "date": upcoming[0].isoformat(),
                    "waste_type": WASTE_TYPES_BY_KEY[key]["name_cs"],
                }
                for key in WASTE_TYPES_BY_KEY
                if (upcoming := self.coordinator.upcoming(key))
            ),
            key=lambda item: item["date"],
        )

        return {
            "street": self._street,
            "waste_type": ", ".join(waste_types) if waste_types else None,
            "waste_types": waste_types,
            "waste_keys": waste_keys,
            **_days_attributes(next_date),
            "upcoming_summary": upcoming_summary,
        }
