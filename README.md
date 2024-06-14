# 🥬 Harvst Watermate for Home Assistant
A custom compontent for Home Assistant to add support for the Harvst Watermate and Sprout greenhouses.

## ⚠️This is an unofficial integration and is not supported by [Harvst](https://www.harvst.co.uk/)

This is an attempt to pull data and control the local web interface of the Harvst Watermate into Home Assistant.

🚧 I have only tested this on my Sprout S24.

## Currently Supported Functions
- 1x Temperature Sensor
- Switch 3 outputs on/off

## Installation (Manual only)

1. Copy the `custom_components/HA-Harvst-Watermate` directory into your Home Assistant `config` directory.

## Post Installation Steps

2. Add the following entry to your `configuration.yaml` file:

    ```yaml
    sensor:
      - platform: harvst_watermate
        host: **IP_OF_YOUR_DEVICE**

    switch:
      - platform: harvst_watermate
        host: **IP_OF_YOUR_DEVICE**
    ```

3. Restart Home Assistant.

## Devices tested on
- Sprout S24 - 4-Season - Firmware 2024060601

## TODO:
- [ ] Add to HACS
- [ ] Reduce number of calls made to device
- [ ] Add control of water pumping (Zone 1 & 2)
- [ ] Add monitoring of water pumping state
- [ ] Add extra device data.
