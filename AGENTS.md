# AGENTS.md - AI Assistant Development Guide

This document provides comprehensive guidance for AI assistants working on the HA-Harvst-Watermate codebase. It covers project structure, development workflows, coding conventions, and important architectural decisions.

## Project Overview

**HA-Harvst-Watermate** is an unofficial Home Assistant custom integration for Harvst Watermate and Sprout greenhouses. It provides local control and monitoring of greenhouse devices through their local web interface.

- **Project Type**: Home Assistant Custom Component
- **License**: MIT
- **Python Version**: 3.12+
- **Home Assistant Minimum Version**: 2024.3.0
- **Integration Type**: Local Polling (no cloud dependency)
- **Repository**: https://github.com/yayadrian/HA-Harvst-Watermate
- **Maintainer**: @yayadrian

### Key Features
- Temperature sensor monitoring
- Three configurable switch outputs (x1, x2, x3)
- Pump running state monitoring (requires firmware 2024061702+)
- Local communication via Server-Sent Events (SSE)

### Tested Hardware
- Sprout S24 - 4-Season (Firmware 2024060601)

---

## Repository Structure

```
HA-Harvst-Watermate/
├── .devcontainer.json              # VS Code dev container configuration
├── .github/
│   └── workflows/
│       ├── hassfest.yaml           # Home Assistant validation workflow
│       └── validate.yaml           # HACS validation workflow
├── .vscode/
│   ├── launch.json                 # VS Code debug configuration
│   ├── settings.json               # VS Code editor settings
│   └── tasks.json                  # VS Code task definitions
├── custom_components/
│   └── harvst_watermate/
│       ├── __init__.py             # Integration setup and entry point
│       ├── binary_sensor.py        # Pump state binary sensor
│       ├── config_flow.py          # Configuration flow (placeholder)
│       ├── const.py                # Constants and domain definition
│       ├── manifest.json           # Integration metadata
│       ├── sensor.py               # Temperature sensor implementation
│       ├── strings.json            # UI strings for config flow
│       ├── switch.py               # Switch output controls
│       └── translations/
│           └── en.json             # English translations
├── scripts/
│   ├── develop                     # Start development HA instance
│   ├── lint                        # Run linting with ruff
│   └── setup                       # Install dependencies
├── .gitattributes                  # Git attributes
├── .gitignore                      # Git ignore patterns
├── .ruff.toml                      # Ruff linter configuration
├── CONTRIBUTING.md                 # Contribution guidelines
├── hacs.json                       # HACS metadata
├── LICENSE                         # MIT License
├── README.md                       # User-facing documentation
└── requirements.txt                # Python dependencies
```

---

## Architecture and Design Patterns

### Integration Architecture

This is a **platform-based** Home Assistant integration using the legacy YAML configuration approach. The integration consists of three main platform types:

1. **Sensor Platform** (`sensor.py`) - Temperature monitoring
2. **Switch Platform** (`switch.py`) - Output control (x1, x2, x3)
3. **Binary Sensor Platform** (`binary_sensor.py`) - Pump state monitoring

### Communication Pattern

The integration uses **Server-Sent Events (SSE)** to poll device state:

- **Endpoint**: `http://<device_ip>/events`
- **Protocol**: HTTP GET with `Accept: text/event-stream` header
- **Data Format**: JSON objects embedded in SSE `data:` events
- **Timeout**: 10-30 seconds per request
- **SSL Verification**: Disabled (`verify=False`)

### Control Pattern

Device control is done via HTTP GET requests:

- **Endpoint**: `http://<device_ip>/control`
- **Parameters**: `?do=<command>` (e.g., `x1On`, `x2Off`)
- **Response**: HTTP 200 on success

### Data Model

The device streams JSON events with the following structure:

```json
{
  "te": 22.5,      // Temperature in Celsius
  "x1": 1,         // Output 1 state (0/1)
  "x2": 0,         // Output 2 state (0/1)
  "x3": 1,         // Output 3 state (0/1)
  "pz": 1          // Pump zone state (0/1)
}
```

### Code Duplication

**IMPORTANT**: The `get_new_reading()` function is duplicated across `sensor.py`, `switch.py`, and `binary_sensor.py`. This is a known architectural issue that should be refactored into a shared utility module or API client class.

---

## Development Workflow

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yayadrian/HA-Harvst-Watermate.git
   cd HA-Harvst-Watermate
   ```

2. **Install dependencies**:
   ```bash
   ./scripts/setup
   ```
   This installs:
   - Home Assistant 2024.6.0
   - colorlog 6.8.2
   - ruff 0.4.9

3. **VS Code DevContainer** (recommended):
   - Open the repository in VS Code
   - Click "Reopen in Container" when prompted
   - The container includes Python 3.12, all extensions, and proper port forwarding for Home Assistant (port 8123)

### Development Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** to the appropriate files in `custom_components/harvst_watermate/`

3. **Run linting** before committing:
   ```bash
   ./scripts/lint
   ```
   This runs `ruff check . --fix` to automatically fix style issues.

4. **Test locally**:
   ```bash
   ./scripts/develop
   ```
   This starts a local Home Assistant instance with:
   - Config directory at `./config`
   - PYTHONPATH set to include `custom_components`
   - Debug mode enabled
   - Available at http://localhost:8123

5. **Commit changes**:
   - Write clear, descriptive commit messages
   - Reference issue numbers when applicable
   - Keep commits focused and atomic

6. **Open a Pull Request**:
   - Fork the repository
   - Push your branch
   - Open a PR against `main`
   - Ensure CI checks pass (hassfest and HACS validation)

### CI/CD Workflows

The project uses GitHub Actions for validation:

1. **Hassfest Validation** (`.github/workflows/hassfest.yaml`):
   - Runs on push, PR, and daily schedule
   - Validates Home Assistant integration structure
   - Checks manifest.json, strings.json, etc.

2. **HACS Validation** (`.github/workflows/validate.yaml`):
   - Runs on push, PR, daily schedule, and manual dispatch
   - Validates HACS integration requirements
   - Checks hacs.json structure

---

## Code Conventions and Style Guide

### Linting and Formatting

The project uses **Ruff** for linting and **Black** for formatting.

**Ruff Configuration** (`.ruff.toml`):
- Target: Python 3.12
- Ruleset: `ALL` (very comprehensive)
- Notable ignores:
  - `ANN101` - Missing type annotation for `self`
  - `ANN401` - Dynamically typed expressions (Any)
  - `D203` - No blank line before class (formatter conflict)
  - `D212` - Multi-line summary first line (formatter conflict)
  - `COM812`, `ISC001` - Formatter conflicts
- Max complexity: 25

**VS Code Settings**:
- Default formatter: Black
- Format on save: Yes
- Format on type: Yes
- Tab size: 4 spaces
- EOL: `\n` (Unix line endings)
- Trim trailing whitespace: Yes (except Markdown)

### Code Style Guidelines

1. **Type Hints**: Use type hints for function parameters and return types
   ```python
   def setup_platform(
       hass: HomeAssistant,
       config: ConfigType,
       add_entities: AddEntitiesCallback,
       discovery_info: DiscoveryInfoType | None = None,
   ) -> None:
   ```

2. **Imports**: Use absolute imports and group them properly
   ```python
   from __future__ import annotations  # Always first

   import json  # Standard library

   import requests  # Third-party

   from homeassistant.components.sensor import SensorEntity  # Home Assistant
   from homeassistant.const import CONF_HOST
   ```

3. **Docstrings**: Use clear docstrings for public functions and classes
   ```python
   def update(self) -> None:
       """Fetch new state data for the sensor.

       This is the only method that should fetch new data for Home Assistant.
       """
   ```

4. **Naming Conventions**:
   - Classes: `PascalCase` (e.g., `TemperatureSilver`, `PumpSensor`)
   - Functions: `snake_case` (e.g., `get_new_reading`, `send_turn_command`)
   - Constants: `UPPER_SNAKE_CASE` (e.g., `DOMAIN`, `CONF_HOST`)
   - Private methods: prefix with `_`

5. **Entity Naming**:
   - Use descriptive names: `"Harvst Main Temperature"`, `"Watermate Pump"`
   - Prefix with device brand: `"Watermate Output1"`

### Home Assistant Specific Conventions

1. **Platform Setup**:
   ```python
   def setup_platform(
       hass: HomeAssistant,
       config: ConfigType,
       add_entities: AddEntitiesCallback,
       discovery_info: DiscoveryInfoType | None = None,
   ) -> None:
       """Set up the sensor platform."""
       host_ip = config.get(CONF_HOST)
       # Create entities
       add_entities([entity1, entity2])
   ```

2. **Entity Attributes**:
   - Use `_attr_` prefix for class attributes
   - Set attributes in `__init__` method
   ```python
   _attr_name = "Harvst Main Temperature"
   _attr_device_class = SensorDeviceClass.TEMPERATURE
   _attr_state_class = SensorStateClass.MEASUREMENT
   ```

3. **Update Method**:
   - Implement `update()` method for polling entities
   - Update `_attr_native_value` or `_attr_is_on`
   - Handle missing values gracefully

---

## Important Implementation Details

### Security Considerations

1. **SSL Verification Disabled**: The integration uses `verify=False` in requests. This is necessary for local devices with self-signed certificates, but it's a security trade-off.

2. **No Authentication**: The device endpoints don't require authentication. Ensure the device is on a trusted network.

3. **Print Statements**: The code contains `print()` statements for debugging. These should be replaced with proper logging using `_LOGGER`.

### Error Handling

**CRITICAL**: The current code has minimal error handling. Key areas needing improvement:

1. **Missing Value Handling**: Recent commit shows awareness of this:
   ```python
   # sensor.py:84
   self._attr_native_value = new_reading.get("te")
   # binary_sensor.py:82
   self._attr_is_on = bool(new_reading.get("pz"))
   ```
   Always use `.get()` with appropriate defaults.

2. **Network Timeouts**: Timeouts vary (10-30 seconds). Consider standardizing.

3. **Request Exceptions**: No try-except blocks around HTTP requests. Should handle:
   - Connection errors
   - Timeouts
   - Invalid JSON
   - HTTP errors

### Domain Name Inconsistency

**BUG**: There's a typo in `const.py`:
```python
DOMAIN = "harvster"  # Should be "harvst_watermate"
```

This doesn't match the manifest.json domain and may cause issues with config flow.

---

## Testing and Quality Assurance

### Manual Testing Checklist

When making changes, test:

1. **Temperature Sensor**:
   - Reads temperature correctly
   - Updates on schedule
   - Handles missing `te` value

2. **Switches**:
   - Can turn on/off
   - State reflects actual device state
   - All three outputs work (x1, x2, x3)

3. **Binary Sensor**:
   - Correctly shows pump running state
   - Requires firmware 2024061702+

4. **Edge Cases**:
   - Device unreachable
   - Malformed JSON responses
   - Network timeouts

### Linting Requirements

Before committing, ensure code passes:
```bash
./scripts/lint
```

If linting fails, fix issues manually or use:
```bash
ruff check . --fix
```

### CI Validation

PRs must pass:
1. **hassfest** - Home Assistant structure validation
2. **HACS** - HACS integration requirements

---

## Known TODOs and Future Work

### From Code Comments

1. **`__init__.py`**:
   - Create API instance/class
   - Validate API connection
   - Store API object in `hass.data[DOMAIN]`

2. **`config_flow.py`**:
   - Replace `PlaceholderHub` with real API client
   - Implement actual authentication (if needed)
   - Adjust schema if no auth required

### From README

- [x] Add to HACS
- [x] Reduce number of calls made to device
- [x] Add monitoring of water pumping state
- [ ] Add control of water pumping (Zone 1 & 2)
- [ ] Add extra device data

### Suggested Architectural Improvements

1. **Refactor `get_new_reading()`**:
   - Create a shared `WatermateClient` class
   - Move HTTP logic to a single location
   - Add proper error handling and logging
   - Implement connection pooling

2. **Replace `print()` with logging**:
   ```python
   import logging
   _LOGGER = logging.getLogger(__name__)
   _LOGGER.debug("Updating: %s", self._attr_name)
   ```

3. **Add proper error handling**:
   ```python
   try:
       new_reading = get_new_reading(self.url_to_events)
       self._attr_native_value = new_reading.get("te")
   except (RequestException, JSONDecodeError, KeyError) as err:
       _LOGGER.error("Failed to update sensor: %s", err)
       self._attr_available = False
   ```

4. **Implement proper config flow**:
   - Remove placeholder authentication
   - Test connection to device
   - Validate IP address format

5. **Add device info**:
   - Register a device in Home Assistant
   - Add firmware version tracking
   - Add model information

6. **Add water pump control**:
   - New switches for Zone 1 and Zone 2 pumps
   - Commands likely similar to output control

---

## Common Pitfalls for AI Assistants

### Things to Avoid

1. **Don't modify manifest.json version** without maintainer approval
2. **Don't change the DOMAIN constant** without updating all references
3. **Don't add external dependencies** without updating:
   - `requirements.txt`
   - `manifest.json` (requirements field)
4. **Don't break YAML configuration compatibility** - users rely on this format
5. **Don't assume firmware capabilities** - some features require specific firmware versions

### Things to Remember

1. **This is a local polling integration** - no cloud, no webhooks
2. **Platform-based setup** - not using config entries properly yet
3. **Code duplication exists** - be consistent when making changes across platforms
4. **SSL verification is disabled** - for local devices only
5. **Tested on one device only** - be cautious with device-specific assumptions

### When Adding Features

1. **Check firmware requirements** - document in code and README
2. **Test with actual hardware** if possible - or clearly mark as untested
3. **Update README.md** with new functionality
4. **Add to appropriate platform** (sensor, switch, binary_sensor)
5. **Follow Home Assistant device class conventions** - use standard device classes

### Code Review Guidelines

When reviewing or generating code, check:

- [ ] Type hints are present and correct
- [ ] Docstrings explain the purpose
- [ ] Error handling for network operations
- [ ] Proper use of `.get()` for dictionary access
- [ ] Logging instead of print statements
- [ ] Consistent with existing code style
- [ ] No hardcoded values (use constants)
- [ ] Entity names are user-friendly
- [ ] Device class is appropriate

---

## Quick Reference

### Key Files to Modify

- **Adding sensors**: `sensor.py`
- **Adding switches**: `switch.py`
- **Adding binary sensors**: `binary_sensor.py`
- **Integration setup**: `__init__.py`
- **Constants**: `const.py`
- **UI strings**: `strings.json`, `translations/en.json`
- **Metadata**: `manifest.json`, `hacs.json`

### Commands

```bash
./scripts/setup          # Install dependencies
./scripts/develop        # Start dev HA instance
./scripts/lint           # Run linter
ruff check . --fix       # Auto-fix linting issues
```

### Important Constants

```python
DOMAIN = "harvster"  # (Note: typo, should match manifest)
CONF_HOST            # Home Assistant constant for host IP
```

### Device Endpoints

```
GET http://<device_ip>/events        # SSE stream of device state
GET http://<device_ip>/control?do=<command>  # Send control command
```

### Control Commands

```
x1On, x1Off  # Output 1
x2On, x2Off  # Output 2
x3On, x3Off  # Output 3
```

---

## Getting Help

- **Issues**: https://github.com/yayadrian/HA-Harvst-Watermate/issues
- **Pull Requests**: Fork the repo and create a PR
- **Documentation**: See README.md and CONTRIBUTING.md
- **Home Assistant Docs**: https://developers.home-assistant.io/

---

## Version History

- **v0.0.3** - Current version (manifest.json)
- Based on integration_blueprint template by @ludeeus

---

**Last Updated**: 2026-01-07
**Document Version**: 1.0.0
