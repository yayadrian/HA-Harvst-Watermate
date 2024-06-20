from __future__ import annotations

import json

import requests

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


def get_new_reading(hosturl):
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
                # return relevant_data

    # Make the HTTP request and handle the SSE stream
    with requests.get(
        hosturl, headers=headers, verify=False, stream=True, timeout=30
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
    """Set up the binary sensor platform."""
    host_ip = config.get(CONF_HOST)

    pumpState = PumpSensor(host_ip=host_ip)

    add_entities([pumpState])


class PumpSensor(BinarySensorEntity):
    """Representation of a Binary Sensor."""

    _attr_name = "Harvst Pump Running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

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
        print("pump status: ")
        print(new_reading)

        self._attr_native_value = new_reading["pz"]
