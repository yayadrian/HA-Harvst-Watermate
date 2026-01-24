"""Sensor platform for Harvst WaterMate."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up Harvst WaterMate sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: HarvstWatermateDataUpdateCoordinator = data["coordinator"]

    async_add_entities([HarvstWatermateTemperatureSensor(coordinator, entry)])


class HarvstWatermateTemperatureSensor(HarvstWatermateEntity, SensorEntity):
    """Representation of the WaterMate ambient temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: HarvstWatermateDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="temperature",
            name="Harvst Main Temperature",
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value from the latest coordinator data."""
        data = self.coordinator.data or {}
        value = data.get("te")
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
