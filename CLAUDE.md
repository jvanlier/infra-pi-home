# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains Docker-based services for a Raspberry Pi smart home setup:
- **home-assistant-amb**: Main Home Assistant instance with custom components
- **frigate**: Video surveillance
- **pi-hole**: Network-wide ad blocker
- **zigbee2mqtt-amb**: Zigbee device integration via MQTT
- **teslamate**: Tesla vehicle tracking
- **samba**: File sharing

## Common Commands

### Home Assistant (Primary Service)

The home-assistant-amb service is the most actively developed component. Commands use `just`:

```bash
cd home-assistant-amb
just build              # Build Docker image with custom components
just test               # Validate Home Assistant configuration
```

The build process creates a custom Docker image based on `ghcr.io/home-assistant/home-assistant:2026.2.2` with two baked-in custom components:
- **adaptive-lighting**: Dynamic light color/brightness adjustment
- **ha-illuminance**: Light level calculations based on weather/sun position

### Pre-commit Hooks

```bash
pre-commit run --all-files    # Run YAML validation and formatting checks
```

Note: Pre-commit excludes Home Assistant blueprint files and configuration.yaml which use special YAML syntax.

## Architecture

### Home Assistant Configuration Structure

Home Assistant config uses a split configuration model (see `home-assistant-amb/config/configuration.yaml`):

- **Directories merged as lists** (`!include_dir_merge_list`):
  - `automation/`: Individual automation YAML files
  - `sensor/`: Sensor definitions
  - `template/`: Template sensors and binary sensors

- **Individual files included** (`!include`):
  - `input_boolean.yaml`, `input_datetime.yaml`, `input_number.yaml`: User inputs
  - `lovelace.yaml`: Dashboard configuration
  - `script.yaml`: Scripts
  - `binary_sensor.yaml`: Binary sensor definitions
  - `adaptive_lighting.yaml`: Adaptive lighting configurations for each light/room
  - `illuminance.yaml`: Illuminance sensor definitions

### Custom Components Symlink Pattern

The Dockerfile installs custom components to `/custom_components`. The mounted config directory contains a symlink `custom_components -> /custom_components`. This allows custom components to be baked into the Docker image while the config directory is mounted at runtime.

### Key Home Assistant Concepts Used

**Adaptive Lighting**: Each light/room has a configuration in `adaptive_lighting.yaml` with settings like:
- `min_brightness`/`max_brightness`: Brightness range
- `min_color_temp`/`max_color_temp`: Color temperature range (Kelvin)
- `sleep_brightness`/`sleep_transition`: Sleep mode behavior
- `max_sunset_time`: Override sunset time for bedrooms

**Motion-Activated Lights**: Custom blueprint `light_motion_activated_dark_aware.yaml` implements:
- Turn on at full adaptive brightness when motion detected
- When no motion and dark: dim to lower percentage instead of turning off
- When no motion and bright/sleep mode: turn off completely
- Respects device-specific no-motion delays

**Presence Detection**: Multi-level presence system (see `template/presence.yaml`):
- Individual sensor timers: Door contacts, motion sensors trigger "recent" binary sensors with auto-off
- Floor-level presence: `Presence Ground Floor` (20 min delay), `Presence First Floor` (15 min), `Presence Second Floor` (5 min)
- House-level presence: `Presence House` combines person locations + floor presence
- Prevents lights from turning off prematurely when moving between rooms

**Dark Awareness**: Binary sensors in `template/dark.yaml`:
- `Sufficiently Dark For Indoor Lights`: Illuminance < threshold (uses `motion_garden_illuminance_filtered`)
- `Sufficiently Dark For Outdoor Lights`: Illuminance < lower threshold
- Uses ha-illuminance component which combines sun elevation + weather cloud coverage

### CI/CD

GitHub Actions workflow validates Home Assistant config on every push to `home-assistant-amb/**`:
1. Builds Docker image
2. Runs `just test-config` (Home Assistant's `hass --script check_config`)

## Making Changes

When modifying Home Assistant configuration:

1. Edit YAML files in `home-assistant-amb/config/`
2. Run `just test` to validate configuration locally
3. Create a branch, commit and push (CI will validate again)
4. To verify on live Home Assistant, assuming the image is unchanged, instruct the user to checkout the branch on Raspberry pi (or simply pull if that has already happened and we're iterating), and reload configuration or restart via UI

When adding/removing adaptive lighting configs, update references in:
- `automation/light_adaptive.yaml`
- `automation/sleep_mode.yaml`
