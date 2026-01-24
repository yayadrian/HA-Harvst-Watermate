# Changelog

## [1.0.0] - 2025-01-24

### Breaking Changes

- **Domain renamed from `harvster` to `harvst_watermate`**: Existing installations will need to remove and re-add the integration. Your previous configuration entries will not be migrated automatically.
- **Configuration method changed**: The integration now uses Home Assistant's config flow UI instead of `configuration.yaml`. Remove any `harvst_watermate` entries from your `configuration.yaml` and add the integration through Settings > Devices & Services > Add Integration.

### Added

- New push-based architecture using Server-Sent Events (SSE) for real-time updates
- Standalone API harness (`scripts/harvst_watermate_harness.py`) for debugging without Home Assistant
- Proper device grouping - all entities now appear under a single "Harvst WaterMate" device
- Exponential backoff with automatic reconnection on connection failures

### Changed

- Migrated from synchronous `requests` library to async `aiohttp`
- Entities now update instantly via SSE push instead of polling
- Simplified config flow - only requires host IP (removed unused username/password fields)

### Fixed

- Reduced network traffic by using a single persistent SSE connection instead of multiple polling requests
