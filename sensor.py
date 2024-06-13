"""Platform for sensor integration."""

from __future__ import annotations

import json

import requests

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


def get_new_reading(url):
    # Set the headers
    headers = {
        "Accept": "text/event-stream",
        "User-Agent": "Mozilla/5.0 (Home Assistant Integration)",
    }

    # Custom event listener
    def handle_event(event):
        if event.startswith("data:"):
            # Extract the data field from the event
            data = event[len("data: ") :].strip()  # Remove leading/trailing whitespace
            if data.startswith("{") and data.endswith("}"):
                # Parse the JSON data
                return json.loads(data)

    # Make the HTTP request and handle the SSE stream
    with requests.get(
        url, headers=headers, verify=False, stream=True, timeout=30
    ) as response:
        for line in response.iter_lines():
            if line:
                relevant_data = handle_event(line.decode("utf-8"))
                if relevant_data:
                    return relevant_data


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    host_ip = config.get(CONF_HOST)

    SilverBullet = TemperatureSilver(host_ip=host_ip)
    add_entities([SilverBullet])


class TemperatureSilver(SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "Harvst Main Temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, host_ip) -> None:
        """Initialize the output."""
        self.url_to_events = "http://" + host_ip + "/events"
        self._attr_is_on = False
        print("Init: " + self._attr_name)

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """

        # Call the function to get a new reading
        new_reading = get_new_reading(self.url_to_events)
        print(new_reading)

        self._attr_native_value = new_reading["te"]
