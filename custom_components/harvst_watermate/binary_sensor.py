"""Binary sensor platform for Harvst WaterMate."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HarvstWatermateDataUpdateCoordinator
from .const import DOMAIN
from .entity import HarvstWatermateEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WaterMate binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: HarvstWatermateDataUpdateCoordinator = data["coordinator"]

    async_add_entities([HarvstWatermatePumpSensor(coordinator, entry)])


class HarvstWatermatePumpSensor(HarvstWatermateEntity, BinarySensorEntity):
    """Representation of the WaterMate pump running state."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: HarvstWatermateDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="pump",
            name="Watermate Pump",
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the pump is reported as running."""
        data = self.coordinator.data or {}
        value = data.get("pz")
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "on"}:
                return True
            if normalized in {"0", "false", "off"}:
                return False
        return bool(value)
