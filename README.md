# 🥬 Harvst Watermate for Home Assistant
A custom compontent for Home Assistant to add support for the Harvst Watermate and Sprout greenhouses.

## ⚠️This is an unofficial integration and is not supported by [Harvst](https://www.harvst.co.uk/)

This is an attempt to pull data and control the local web interface of the Harvst Watermate into Home Assistant.

🚧 I have only tested this on my Sprout S24.

## Currently Supported Functions
- 1x Temperature Sensor
- Switch 3 outputs on/off
- Monitoring Pump Running State - _Requires Firmware 2024061702_

## Installation 

### HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yayadrian&repository=HA-Harvst-Watermate&category=Integration)


### Manual Installation
<details>
<summary>More Details</summary>

* You should take the latest [published release](https://github.com/yayadrian/HA-Harvst-Watermate/releases/).  
* To install, place the contents of `custom_components` into the `<config directory>/custom_components` folder of your Home Assistant installation.  
</details>

## Post Installation Steps

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for "Harvst WaterMate"
3. Enter the IP address of your WaterMate device
4. The integration will create a device with all sensors and switches

## Upgrading from v0.x

Version 1.0.0 includes breaking changes. If you were using a previous version:

1. Remove any `harvst_watermate` entries from your `configuration.yaml`
2. Remove the old integration from **Settings** > **Devices & Services**
3. Restart Home Assistant
4. Re-add the integration using the steps above

See [CHANGELOG.md](CHANGELOG.md) for full details.

## Standalone API Harness

Need to debug the WaterMate API without loading the Home Assistant integration? A lightweight CLI harness is available in `scripts/harvst_watermate_harness.py`.

1. Create and activate a virtual environment (optional, but recommended):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

1. Install the minimal dependencies:

    ```bash
    python -m pip install aiohttp==3.9.5 async_timeout==4.0.3
    ```

1. Export your WaterMate host/IP or pass it via `--host` when running the harness:

    ```bash
    export HARVST_WATERMATE_HOST=192.168.1.42
    ```

1. Run one of the available commands:

    ```bash
    # Stream a couple of events
    python scripts/harvst_watermate_harness.py events --limit 5

    # Send a control command (valid outputs: x1, x2, x3)
    python scripts/harvst_watermate_harness.py set-output x1 on

    # Perform a connection test (exits after first payload)
    python scripts/harvst_watermate_harness.py test
    ```

Commands exit with non-zero status codes on network/authentication errors, so they can be chained in scripts or CI runs.

## Devices tested on

- Sprout S24 - 4-Season - Firmware 2024060601

## TODO

- [x] Add to HACS
- [x] Reduce number of calls made to device
- [x] Add monitoring of water pumping state
- [ ] Add control of water pumping (Zone 1 & 2)
- [ ] Add extra device data.
