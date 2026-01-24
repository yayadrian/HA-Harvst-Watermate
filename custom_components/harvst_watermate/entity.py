"""Shared entity model for Harvst WaterMate."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN


class HarvstWatermateEntity(CoordinatorEntity):
    """Base class for Harvst WaterMate entities."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        *,
        unique_suffix: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}-{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=DEFAULT_NAME,
            manufacturer="Harvst",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )
        self._attr_has_entity_name = True
