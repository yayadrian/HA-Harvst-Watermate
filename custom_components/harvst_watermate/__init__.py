"""The Harvst WaterMate integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, Platform
from homeassistant.exceptions import ConfigEntryNotReady

from .api import WaterMateAPI
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Harvst WaterMate from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API instance
    api = WaterMateAPI(entry.data[CONF_HOST])

    # Test the connection
    host = entry.data[CONF_HOST]
    if not await api.test_connection():
        msg = f"Cannot connect to WaterMate device at {host}"
        raise ConfigEntryNotReady(msg)

    # Store API object for platforms to access
    hass.data[DOMAIN][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
