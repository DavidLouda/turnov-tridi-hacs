"""Base entity for Turnov Třídí."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_STREET, DOMAIN
from .coordinator import TurnovTridiCoordinator


class TurnovTridiEntity(CoordinatorEntity[TurnovTridiCoordinator]):
    """Entity belonging to the waste collection service of one street."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TurnovTridiCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._street: str = entry.data[CONF_STREET]
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Svoz odpadu – {self._street}",
            manufacturer="Město Turnov",
            model="Svoz odpadu",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Stay available with the last known schedule while the website is down."""
        return super().available or bool(self.coordinator.data)
