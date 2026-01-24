"""Switch platform for Harvst WaterMate."""

from __future__ import annotations

from typing import Final

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HarvstWatermateDataUpdateCoordinator
from .api import HarvstWatermateApiClient, HarvstWatermateApiClientError
from .const import DOMAIN
from .entity import HarvstWatermateEntity

OUTPUTS: Final[tuple[tuple[str, str], ...]] = (
    ("x1", "Watermate Output 1"),
    ("x2", "Watermate Output 2"),
    ("x3", "Watermate Output 3"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WaterMate switches from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: HarvstWatermateDataUpdateCoordinator = data["coordinator"]
    api: HarvstWatermateApiClient = data["api"]

    entities = [
        HarvstWatermateSwitch(coordinator, entry, api, output_id, name)
        for output_id, name in OUTPUTS
    ]

    async_add_entities(entities)


class HarvstWatermateSwitch(HarvstWatermateEntity, SwitchEntity):
    """Representation of a WaterMate controllable output."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(
        self,
        coordinator: HarvstWatermateDataUpdateCoordinator,
        entry: ConfigEntry,
        api: HarvstWatermateApiClient,
        output_id: str,
        name: str,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix=f"switch-{output_id}",
            name=name,
        )
        self._api = api
        self._output_id = output_id

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        value = data.get(self._output_id)
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

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_send_command(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_send_command(False)

    async def _async_send_command(self, turn_on: bool) -> None:
        try:
            await self._api.async_set_output(self._output_id, turn_on)
        except HarvstWatermateApiClientError as err:
            raise HomeAssistantError(
                f"Unable to set {self.name} to {'on' if turn_on else 'off'}: {err}"
            ) from err

        await self.coordinator.async_request_refresh()
