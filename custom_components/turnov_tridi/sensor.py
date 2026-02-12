"""Sensor platform for Turnov Třídí integration."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_STREET, DOMAIN, WASTE_TYPES
from .coordinator import TurnovTridiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Turnov Třídí sensors from a config entry."""
    coordinator: TurnovTridiCoordinator = hass.data[DOMAIN][entry.entry_id]
    street = entry.data[CONF_STREET]

    entities: list[SensorEntity] = []

    # Create a sensor for each waste type
    for css_class, waste_info in WASTE_TYPES.items():
        entities.append(
            TurnovTridiWasteSensor(
                coordinator=coordinator,
                street=street,
                waste_key=waste_info["key"],
                waste_name_cs=waste_info["name_cs"],
                waste_name_en=waste_info["name_en"],
                waste_icon=waste_info["icon"],
                entry_id=entry.entry_id,
            )
        )

    # Create a "next collection" sensor showing the soonest pickup
    entities.append(
        TurnovTridiNextCollectionSensor(
            coordinator=coordinator,
            street=street,
            entry_id=entry.entry_id,
        )
    )

    async_add_entities(entities)


class TurnovTridiWasteSensor(
    CoordinatorEntity[TurnovTridiCoordinator], SensorEntity
):
    """Sensor for a specific waste type collection schedule."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TurnovTridiCoordinator,
        street: str,
        waste_key: str,
        waste_name_cs: str,
        waste_name_en: str,
        waste_icon: str,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._street = street
        self._waste_key = waste_key
        self._waste_name_cs = waste_name_cs
        self._attr_unique_id = f"{entry_id}_{waste_key}"
        self._attr_translation_key = waste_key
        self._attr_icon = waste_icon
        self._attr_name = waste_name_cs

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id.rsplit("_", 1)[0])},
            "name": f"Svoz odpadu – {self._street}",
            "manufacturer": "Město Turnov",
            "model": "Svoz odpadu",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> date | None:
        """Return the next collection date for this waste type."""
        if not self.coordinator.data:
            return None

        dates = self.coordinator.data.get(self._waste_key, [])
        today = date.today()

        for d in dates:
            if d >= today:
                return d
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs: dict[str, Any] = {
            "street": self._street,
            "waste_type": self._waste_name_cs,
        }

        if not self.coordinator.data:
            return attrs

        dates = self.coordinator.data.get(self._waste_key, [])
        today = date.today()
        upcoming = [d for d in dates if d >= today]

        if upcoming:
            days_until = (upcoming[0] - today).days
            attrs["days_until"] = days_until
            attrs["is_tomorrow"] = days_until == 1
            attrs["is_today"] = days_until == 0
            attrs["upcoming_dates"] = [d.isoformat() for d in upcoming[:5]]
        else:
            attrs["days_until"] = None
            attrs["is_tomorrow"] = False
            attrs["is_today"] = False
            attrs["upcoming_dates"] = []

        return attrs


class TurnovTridiNextCollectionSensor(
    CoordinatorEntity[TurnovTridiCoordinator], SensorEntity
):
    """Sensor showing the very next waste collection of any type."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-alert"
    _attr_name = "Nejbližší svoz"

    def __init__(
        self,
        coordinator: TurnovTridiCoordinator,
        street: str,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._street = street
        self._attr_unique_id = f"{entry_id}_next_collection"
        self._attr_translation_key = "next_collection"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id.rsplit("_", 2)[0])},
            "name": f"Svoz odpadu – {self._street}",
            "manufacturer": "Město Turnov",
            "model": "Svoz odpadu",
            "entry_type": "service",
        }

    @property
    def native_value(self) -> date | None:
        """Return the nearest collection date."""
        next_date, _ = self._get_next_collection()
        return next_date

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs: dict[str, Any] = {"street": self._street}

        next_date, next_type = self._get_next_collection()

        if next_date:
            today = date.today()
            days_until = (next_date - today).days
            attrs["waste_type"] = next_type
            attrs["days_until"] = days_until
            attrs["is_tomorrow"] = days_until == 1
            attrs["is_today"] = days_until == 0

            # Build a summary of all upcoming collections
            all_upcoming: list[dict[str, str]] = []
            if self.coordinator.data:
                for waste_info in WASTE_TYPES.values():
                    dates = self.coordinator.data.get(waste_info["key"], [])
                    for d in dates:
                        if d >= today:
                            all_upcoming.append(
                                {
                                    "date": d.isoformat(),
                                    "waste_type": waste_info["name_cs"],
                                }
                            )
                            break  # only the next one per type

            all_upcoming.sort(key=lambda x: x["date"])
            attrs["upcoming_summary"] = all_upcoming
        else:
            attrs["waste_type"] = None
            attrs["days_until"] = None
            attrs["is_tomorrow"] = False
            attrs["is_today"] = False
            attrs["upcoming_summary"] = []

        return attrs

    def _get_next_collection(self) -> tuple[date | None, str | None]:
        """Find the next collection date across all waste types."""
        if not self.coordinator.data:
            return None, None

        today = date.today()
        nearest_date: date | None = None
        nearest_type: str | None = None

        for waste_info in WASTE_TYPES.values():
            dates = self.coordinator.data.get(waste_info["key"], [])
            for d in dates:
                if d >= today:
                    if nearest_date is None or d < nearest_date:
                        nearest_date = d
                        nearest_type = waste_info["name_cs"]
                    break

        return nearest_date, nearest_type
