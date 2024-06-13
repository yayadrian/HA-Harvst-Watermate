"""Platform for Switch integration."""

from __future__ import annotations

import json

import requests

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
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


def send_turn_command(output, host_ip, state):
    # 'x1Off' - output1
    # Define the URL and parameters
    url = "http://" + host_ip + "/control"
    turn_command = output + state
    params = {"do": turn_command}

    # Set the minimal headers (you may need to adjust these based on the server's requirements)
    headers = {
        "Accept": "*/*",
        "User-Agent": "Mozilla/5.0 (Home Assistant Integration)",
    }

    # Send the request
    response = requests.get(
        url, headers=headers, params=params, verify=False, timeout=30
    )

    # Check if the response is successful
    if response.status_code == 200:
        print("Success: The command was executed successfully.")
        return True
    else:
        print(f"Error: The request failed with status code {response.status_code}.")
        return False


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    host_ip = config.get(CONF_HOST)

    x1_switch = SwitchOutput(
        name="Watermate Output1",
        device_class=SwitchDeviceClass.SWITCH,
        host_ip=host_ip,
        output_id="x1",
    )

    x2_switch = SwitchOutput(
        name="Watermate Output2",
        device_class=SwitchDeviceClass.SWITCH,
        host_ip=host_ip,
        output_id="x2",
    )

    x3_switch = SwitchOutput(
        name="Watermate Output3",
        device_class=SwitchDeviceClass.SWITCH,
        host_ip=host_ip,
        output_id="x3",
    )

    add_entities([x1_switch, x2_switch, x3_switch])


class SwitchOutput(SwitchEntity):
    """Representation of a Switch."""

    def __init__(self, name, device_class, host_ip, output_id) -> None:
        """Initialize the output."""
        self._attr_name = name
        self._attr_device_class = device_class
        self.host_ip = host_ip
        self.url_to_events = "http://" + host_ip + "/events"
        self.output_id = output_id
        self._attr_is_on = False
        print("Init: " + self._attr_name)

    def turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        result = send_turn_command(self.output_id, self.host_ip, "On")
        self._attr_is_on = result

    def turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        result = send_turn_command(self.output_id, self.host_ip, "Off")
        self._attr_is_on = result

    def update(self) -> None:
        """Update the state of the entity."""
        print("Updating: " + self._attr_name)
        new_reading = get_new_reading(self.url_to_events)
        self._attr_is_on = bool(new_reading.get(self.output_id))
