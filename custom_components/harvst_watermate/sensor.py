"""Platform for sensor integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import WaterMateAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WaterMate sensor entities from a config entry."""
    api: WaterMateAPI = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WaterMateTemperatureSensor(
            api=api,
            name="WaterMate Temperature",
            unique_id=f"{entry.entry_id}_temperature",
        ),
    ]

    async_add_entities(entities)


class WaterMateTemperatureSensor(SensorEntity):
    """Representation of a WaterMate Temperature Sensor."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        api: WaterMateAPI,
        name: str,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        self._api = api
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_value = None
        _LOGGER.debug("Initialized temperature sensor: %s", name)

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Updating temperature sensor: %s", self._attr_name)
        data = await self._api.get_quick_reading()
        if data:
            self._attr_native_value = data.get("te")
