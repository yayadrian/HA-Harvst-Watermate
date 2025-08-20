"""API client for Harvst WaterMate devices."""

from __future__ import annotations

import json
import logging
from typing import Any

import requests
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 30
SSE_TIMEOUT = 10
DEFAULT_HEADERS = {
    "Accept": "text/event-stream",
    "User-Agent": "Mozilla/5.0 (Home Assistant Integration)",
}
CONTROL_HEADERS = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Home Assistant Integration)",
}
HTTP_OK = 200


class WaterMateConnectionError(HomeAssistantError):
    """Error to indicate we cannot connect to the device."""


class WaterMateAPIError(HomeAssistantError):
    """Error to indicate an API error occurred."""


class WaterMateAPI:
    """API client for Harvst WaterMate devices."""

    def __init__(self, host: str) -> None:
        """Initialize the API client."""
        self.host = host
        self.base_url = f"http://{host}"
        self.events_url = f"{self.base_url}/events"
        self.control_url = f"{self.base_url}/control"

    async def get_device_data(self) -> dict[str, Any] | None:
        """Get current device data via server-sent events."""
        try:
            return self._get_sse_data(self.events_url, REQUEST_TIMEOUT)
        except requests.RequestException as err:
            error_msg = f"Failed to get device data from {self.host}"
            _LOGGER.exception(error_msg)
            raise WaterMateConnectionError(error_msg) from err
        except json.JSONDecodeError as err:
            error_msg = f"Invalid response from {self.host}"
            _LOGGER.exception(error_msg)
            raise WaterMateAPIError(error_msg) from err

    async def get_quick_reading(self) -> dict[str, Any] | None:
        """Get a quick reading with shorter timeout for frequent updates."""
        try:
            return self._get_sse_data(self.events_url, SSE_TIMEOUT)
        except requests.RequestException as err:
            _LOGGER.debug("Quick reading failed from %s: %s", self.host, err)
            return None
        except json.JSONDecodeError as err:
            _LOGGER.warning("Invalid JSON in quick reading from %s: %s", self.host, err)
            return None

    def _get_sse_data(self, url: str, timeout: int) -> dict[str, Any] | None:
        """Get data from server-sent events stream."""
        with requests.get(
            url,
            headers=DEFAULT_HEADERS,
            verify=False,  # TODO: Implement proper SSL handling
            stream=True,
            timeout=timeout,
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    data = self._parse_sse_event(line.decode("utf-8"))
                    if data:
                        return data
        return None

    def _parse_sse_event(self, event: str) -> dict[str, Any] | None:
        """Parse a server-sent event line."""
        if not event.startswith("data:"):
            return None

        data = event[len("data: "):].strip()
        if data.startswith("{") and data.endswith("}"):
            return json.loads(data)
        return None

    async def send_control_command(self, output: str, state: str) -> bool:
        """Send a control command to the device."""
        command = f"{output}{state}"
        params = {"do": command}

        try:
            response = requests.get(
                self.control_url,
                headers=CONTROL_HEADERS,
                params=params,
                verify=False,  # TODO: Implement proper SSL handling
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == HTTP_OK:
                _LOGGER.debug("Successfully sent command %s to %s", command, self.host)
                return True

            _LOGGER.error(
                "Command %s failed for %s: HTTP %d", command, self.host, response.status_code
            )
            return False

        except requests.RequestException:
            _LOGGER.exception("Failed to send command %s to %s", command, self.host)
            return False

    async def test_connection(self) -> bool:
        """Test if we can connect to the device."""
        try:
            data = await self.get_device_data()
            return data is not None
        except (WaterMateConnectionError, WaterMateAPIError):
            return False
