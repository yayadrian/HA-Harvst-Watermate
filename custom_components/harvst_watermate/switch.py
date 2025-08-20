"""Platform for Switch integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity

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
    """Set up WaterMate switch entities from a config entry."""
    api: WaterMateAPI = hass.data[DOMAIN][entry.entry_id]

    entities = [
        WaterMateSwitch(
            api=api,
            name="WaterMate Output 1",
            output_id="x1",
            unique_id=f"{entry.entry_id}_output_1",
        ),
        WaterMateSwitch(
            api=api,
            name="WaterMate Output 2",
            output_id="x2",
            unique_id=f"{entry.entry_id}_output_2",
        ),
        WaterMateSwitch(
            api=api,
            name="WaterMate Output 3",
            output_id="x3",
            unique_id=f"{entry.entry_id}_output_3",
        ),
    ]

    async_add_entities(entities)


class WaterMateSwitch(SwitchEntity):
    """Representation of a WaterMate Switch."""

    def __init__(
        self,
        api: WaterMateAPI,
        name: str,
        output_id: str,
        unique_id: str,
    ) -> None:
        """Initialize the switch."""
        self._api = api
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._output_id = output_id
        self._attr_is_on = False
        _LOGGER.debug("Initialized switch: %s", name)

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the entity on."""
        success = await self._api.send_control_command(self._output_id, "On")
        if success:
            self._attr_is_on = True

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the entity off."""
        success = await self._api.send_control_command(self._output_id, "Off")
        if success:
            self._attr_is_on = False

    async def async_update(self) -> None:
        """Update the state of the entity."""
        _LOGGER.debug("Updating switch: %s", self._attr_name)
        data = await self._api.get_quick_reading()
        if data:
            self._attr_is_on = bool(data.get(self._output_id, False))
