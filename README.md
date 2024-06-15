# 🥬 Harvst Watermate for Home Assistant
A custom compontent for Home Assistant to add support for the Harvst Watermate and Sprout greenhouses.

## ⚠️This is an unofficial integration and is not supported by [Harvst](https://www.harvst.co.uk/)

This is an attempt to pull data and control the local web interface of the Harvst Watermate into Home Assistant.

🚧 I have only tested this on my Sprout S24.

## Currently Supported Functions
- 1x Temperature Sensor
- Switch 3 outputs on/off

## Installation 



### HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yay-adrian&repository=HA-Harvst-Watermate&category=Integration)

Or
Search for `Harvst Watermate` in HACS and install it under the "Integrations" category.

### Manual Installation
<details>
<summary>More Details</summary>

* You should take the latest [published release]([https://github.com/andrew-codechimp/ha-battery-notes/releases](https://github.com/yayadrian/HA-Harvst-Watermate/releases/).  
* To install, place the contents of `custom_components` into the `<config directory>/custom_components` folder of your Home Assistant installation.  
</details>

## Post Installation Steps
1. Add the following entry to your `configuration.yaml` file:

    ```yaml
    sensor:
      - platform: harvst_watermate
        host: **IP_OF_YOUR_DEVICE**

    switch:
      - platform: harvst_watermate
        host: **IP_OF_YOUR_DEVICE**
    ```

2. Restart Home Assistant.

## Devices tested on
- Sprout S24 - 4-Season - Firmware 2024060601

## TODO:
- [x] Add to HACS
- [ ] Reduce number of calls made to device
- [ ] Add control of water pumping (Zone 1 & 2)
- [ ] Add monitoring of water pumping state
- [ ] Add extra device data.
