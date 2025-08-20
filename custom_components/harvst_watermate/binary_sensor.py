"""Platform for binary sensor integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

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
    """Set up WaterMate binary sensor entities from a config entry."""
    api: WaterMateAPI = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WaterMatePumpSensor(
            api=api,
            name="WaterMate Pump",
            unique_id=f"{entry.entry_id}_pump",
        ),
    ]

    async_add_entities(entities)


class WaterMatePumpSensor(BinarySensorEntity):
    """Representation of a WaterMate Pump Binary Sensor."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        api: WaterMateAPI,
        name: str,
        unique_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        self._api = api
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_is_on = False
        _LOGGER.debug("Initialized pump sensor: %s", name)

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Updating pump sensor: %s", self._attr_name)
        data = await self._api.get_quick_reading()
        if data:
            self._attr_is_on = bool(data.get("pz", False))
