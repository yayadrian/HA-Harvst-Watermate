# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for the Harvst WaterMate greenhouse controller. It communicates with the WaterMate device over the local network via HTTP, using Server-Sent Events (SSE) for real-time push updates.

## Development Commands

### Standalone API Testing (without Home Assistant)

```bash
# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install aiohttp==3.9.5 async_timeout==4.0.3

# Test connectivity
export HARVST_WATERMATE_HOST=192.168.1.42
python scripts/harvst_watermate_harness.py test

# Stream events
python scripts/harvst_watermate_harness.py events --limit 5

# Send control command
python scripts/harvst_watermate_harness.py set-output x1 on
```

### Installation for Testing in Home Assistant

Copy `custom_components/harvst_watermate/` to your Home Assistant's `custom_components` directory and restart.

## Architecture

### Data Flow

The integration uses a push-based architecture via SSE rather than polling:

1. `HarvstWatermateApiClient` (api.py) connects to `http://{host}/events` and parses the SSE stream using `_SSEParser`
2. `HarvstWatermateDataUpdateCoordinator` (__init__.py) maintains a persistent listener task that processes SSE messages
3. Entity platforms (sensor.py, switch.py, binary_sensor.py) use `CoordinatorEntity` to automatically update when coordinator data changes

### Key Components

- **api.py**: Low-level HTTP client with SSE parsing. Handles `/events` (read) and `/control` (write) endpoints
- **__init__.py**: Contains `HarvstWatermateDataUpdateCoordinator` which manages the SSE listener lifecycle with exponential backoff (`_ReconnectBackoff`)
- **entity.py**: Base `HarvstWatermateEntity` class providing common device info and unique ID generation
- **config_flow.py**: UI-based configuration flow for adding the integration

### Device Data Keys

The WaterMate streams JSON with these keys:
- `te`: Temperature reading
- `x1`, `x2`, `x3`: Output switch states
- `pz`: Pump running state

### Control Commands

Outputs are controlled via GET requests to `/control?do={output_id}{On|Off}` (e.g., `x1On`, `x2Off`).
