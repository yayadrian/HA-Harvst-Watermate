"""The Harvst WaterMate integration."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from enum import Enum
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    HarvstWatermateApiClient,
    HarvstWatermateApiClientAuthenticationError,
    HarvstWatermateApiClientCommunicationError,
    HarvstWatermateApiClientError,
    SSEMessage,
)
from .const import DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SWITCH, Platform.SENSOR]


class _ListenerState(Enum):
    IDLE = "idle"
    HEALTHY = "healthy"
    ERROR = "error"
    STOPPED = "stopped"


class _ReconnectBackoff:
    """Simple exponential backoff helper respecting SSE retry hints."""

    def __init__(self, *, base: float = 1.0, factor: float = 2.0, maximum: float = 60.0) -> None:
        self._base = base
        self._factor = factor
        self._maximum = maximum
        self._attempt = 0
        self._override: float | None = None

    def reset(self) -> None:
        self._attempt = 0

    def apply_retry_hint(self, retry_ms: int | None) -> None:
        if retry_ms is None:
            return
        self._override = max(retry_ms / 1000.0, self._base)

    def next_delay(self) -> float:
        if self._override is not None:
            delay = self._override
            self._override = None
            self._attempt = 0
            return delay
        delay = min(self._base * (self._factor**self._attempt), self._maximum)
        self._attempt += 1
        return delay


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Harvester from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)
    api_client = HarvstWatermateApiClient(entry.data[CONF_HOST], session)

    coordinator = HarvstWatermateDataUpdateCoordinator(hass, api_client)

    _LOGGER.info(
        "Setting up Harvst WaterMate entry %s for host %s",
        entry.entry_id,
        entry.data[CONF_HOST],
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except HarvstWatermateApiClientAuthenticationError as err:
        await coordinator.async_shutdown()
        raise ConfigEntryAuthFailed(str(err)) from err
    except HarvstWatermateApiClientCommunicationError as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(err) from err
    except HarvstWatermateApiClientError as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(err) from err

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api_client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id)
    coordinator: HarvstWatermateDataUpdateCoordinator | None = None
    if data:
        coordinator = data.get("coordinator")

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if coordinator:
            await coordinator.async_shutdown()
        _LOGGER.info("Unloaded Harvst WaterMate entry %s", entry.entry_id)
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class HarvstWatermateDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate push updates from the WaterMate device."""

    _REFRESH_TIMEOUT = 30

    def __init__(self, hass: HomeAssistant, api_client: HarvstWatermateApiClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DEFAULT_NAME,
            update_interval=None,
        )
        self.api_client = api_client
        self._listener_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._startup_future: asyncio.Future[None] = hass.loop.create_future()
        self._listener_state = _ListenerState.IDLE
        self._backoff = _ReconnectBackoff()
        self._refresh_waiter: asyncio.Future[dict[str, Any]] | None = None

    async def async_config_entry_first_refresh(self) -> None:
        """Start the listener and wait for the first payload."""
        self._ensure_listener_running()
        try:
            await asyncio.wait_for(self._startup_future, timeout=self._REFRESH_TIMEOUT)
        except asyncio.TimeoutError as err:
            raise ConfigEntryNotReady("Timed out waiting for first update from device") from err
        except asyncio.CancelledError:
            _LOGGER.debug("First refresh was cancelled")
            raise
        except HarvstWatermateApiClientAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HarvstWatermateApiClientError as err:
            raise ConfigEntryNotReady(err) from err

    def _ensure_listener_running(self) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        if self._listener_task and self._listener_task.done():
            self._listener_task = None
        self._stop_event.clear()
        self._listener_task = self.hass.loop.create_task(
            self._run_listener(),
            name="harvst_watermate_sse_listener",
        )

    async def _run_listener(self) -> None:
        retry_backoff = self._backoff

        async def _handle_message(message: SSEMessage) -> None:
            retry_backoff.apply_retry_hint(message.retry)
            if message.payload is None:
                return
            retry_backoff.reset()
            if self._listener_state is not _ListenerState.HEALTHY:
                self._update_listener_state(_ListenerState.HEALTHY)
            self.async_set_updated_data(message.payload)
            if not self._startup_future.done():
                self._startup_future.set_result(None)
            if self._refresh_waiter and not self._refresh_waiter.done():
                self._refresh_waiter.set_result(message.payload)

        while not self._stop_event.is_set():
            try:
                await self.api_client.async_listen_events(_handle_message, stop_event=self._stop_event)
                if self._stop_event.is_set():
                    break
                raise HarvstWatermateApiClientCommunicationError("Events stream closed unexpectedly")
            except HarvstWatermateApiClientAuthenticationError as err:
                self._handle_listener_error(err, fatal=True)
                return
            except HarvstWatermateApiClientError as err:
                self._handle_listener_error(err, fatal=False)
            except asyncio.CancelledError:
                break

            if self._stop_event.is_set():
                break

            delay = retry_backoff.next_delay()
            try:
                await asyncio.wait_for(self._stop_event.wait(), delay)
            except asyncio.TimeoutError:
                continue
        self._update_listener_state(_ListenerState.STOPPED)

    def _handle_listener_error(
        self,
        err: HarvstWatermateApiClientError,
        *,
        fatal: bool,
    ) -> None:
        if not self._startup_future.done():
            self._startup_future.set_exception(err)
        if self._refresh_waiter and not self._refresh_waiter.done():
            self._refresh_waiter.set_exception(err)
        self._update_listener_state(_ListenerState.ERROR, err=err)
        if fatal:
            self._stop_event.set()

    def _update_listener_state(
        self,
        new_state: _ListenerState,
        *,
        err: Exception | None = None,
    ) -> None:
        previous = self._listener_state
        if previous == new_state:
            return
        self._listener_state = new_state

        if new_state == _ListenerState.HEALTHY:
            if previous == _ListenerState.ERROR:
                _LOGGER.info("WaterMate events listener recovered")
            elif previous == _ListenerState.IDLE:
                _LOGGER.debug("WaterMate events listener established connection")
        elif new_state == _ListenerState.ERROR:
            if previous == _ListenerState.HEALTHY:
                detail = f": {err}" if err else ""
                _LOGGER.warning("WaterMate events listener entered error state%s", detail)
        elif new_state == _ListenerState.STOPPED:
            _LOGGER.debug("WaterMate events listener stopped")

    async def _async_update_data(self) -> dict[str, Any]:
        """Allow manual refresh calls to await the next push update."""
        self._ensure_listener_running()
        if self._refresh_waiter and not self._refresh_waiter.done():
            waiter = self._refresh_waiter
        else:
            waiter = self.hass.loop.create_future()
            self._refresh_waiter = waiter

        try:
            return await asyncio.wait_for(waiter, timeout=self._REFRESH_TIMEOUT)
        except asyncio.TimeoutError as err:
            if self._refresh_waiter is waiter and not waiter.done():
                waiter.cancel()
                self._refresh_waiter = None
            raise UpdateFailed("Timed out waiting for WaterMate push update") from err
        finally:
            if self._refresh_waiter is waiter and waiter.done():
                self._refresh_waiter = None

    async def async_shutdown(self) -> None:
        """Stop the listener and clean up resources."""
        self._stop_event.set()
        if not self._listener_task:
            return
        listener = self._listener_task
        self._listener_task = None
        listener.cancel()
        with suppress(asyncio.CancelledError):
            await listener
