# TeslaMate Battery Level Sensor Implementation Plan

**Goal:** Surface the Tesla's battery percentage (published by TeslaMate over MQTT) as a Home Assistant sensor entity, with a badge on the Overview dashboard.

**Architecture:** Home Assistant already has a working MQTT integration config entry (set up via the UI, used today for zigbee2mqtt discovery) connected to the shared `mqtt` broker container. TeslaMate publishes plain (non-discovery) MQTT topics under `teslamate/cars/<car_id>/...` to that same broker. This plan adds one manually-defined MQTT sensor via the `mqtt:` YAML integration key (a new `mqtt.yaml` include file, following this repo's existing single-file-include pattern), then exposes it on the Overview dashboard.

**Tech Stack:** Home Assistant (`ghcr.io/home-assistant/home-assistant:2026.5.2`), YAML configuration, Mosquitto MQTT broker, TeslaMate (already running, already connected to the broker - no TeslaMate-side changes needed), `just` task runner, Docker.

## Global Constraints

- Repo root: `/Users/jori.vanlier/dev/private/infra-pi-home` (adjust if the builder's checkout path differs; all paths below are relative to repo root).
- All Home Assistant config lives under `home-assistant-amb/config/`.
- Car id in TeslaMate's MQTT topics is `1` (user confirmed: single car in TeslaMate).
- Use the `battery_level` topic (raw SoC), not `usable_battery_level` (user confirmed).
- Tie sensor availability to the `healthy` topic - sensor shows `unavailable` when TeslaMate's logger for that car is unhealthy (user confirmed).
- Entity name is exactly `Tesla Battery Level` → `unique_id: tesla_battery_level` → `entity_id: sensor.tesla_battery_level` (user confirmed).
- Add a badge for this sensor to the Overview dashboard (`home-assistant-amb/config/dashboard/overview.yaml`), short label `Tesla` (user confirmed).
- Do NOT touch the MQTT broker connection itself (host/port) - that is an existing UI-managed config entry, out of scope.
- Do NOT add any other TeslaMate sensors, a new dashboard/view, or an `mqtt/` directory split - single sensor, single file, YAGNI.
- Validate every change with `just build && just test` run from `home-assistant-amb/` before committing. If `just test` has no output and exits 0, it passed. Never commit if it fails.
- This is a config-only change (no `Dockerfile` or image tag edits) - no `docker compose up -d --build` needed on deploy, only a HA config reload/restart.
- Base branch is `main`. Work happens on a new branch, pushed for CI (`.github/workflows/build-and-test-ha-amb.yml`) to validate again.

---

### Task 1: Add the TeslaMate battery MQTT sensor

**Files:**
- Create: `home-assistant-amb/config/mqtt.yaml`
- Modify: `home-assistant-amb/config/configuration.yaml:29` (insert one line after the `light:` include)
- Modify: `CLAUDE.md:62` (insert one doc bullet after the `adaptive_lighting.yaml` bullet)

**Interfaces:**
- Produces: HA entity `sensor.tesla_battery_level` (`unique_id: tesla_battery_level`, friendly name `Tesla Battery Level`, unit `%`, `device_class: battery`, `state_class: measurement`). Task 2 consumes this exact `entity_id`.

- [ ] **Step 1: Create a feature branch**

Run:
```bash
git checkout main
git pull
git checkout -b feat/teslamate-battery-sensor
```
Expected: branch created and checked out, working tree clean.

- [ ] **Step 2: Create `home-assistant-amb/config/mqtt.yaml`**

This is the first manually-defined MQTT entity in this repo. It's included as the top-level `mqtt:` key in `configuration.yaml` (Task step 3) - a different mechanism than the `sensor: !include_dir_merge_list sensor/` directory used for template/filter sensors elsewhere in this repo.

```yaml
sensor:
  - name: "Tesla Battery Level"
    unique_id: tesla_battery_level
    state_topic: "teslamate/cars/1/battery_level"
    unit_of_measurement: "%"
    device_class: battery
    state_class: measurement
    availability_topic: "teslamate/cars/1/healthy"
    payload_available: "true"
    payload_not_available: "false"
```

Notes for the implementer:
- `teslamate/cars/1/battery_level` publishes a plain integer payload (e.g. `88`), no JSON, no `value_template` needed.
- `teslamate/cars/1/healthy` publishes the plain string `true` or `false` - matches `payload_available`/`payload_not_available` exactly (case-sensitive).
- `device_class: battery` gives this entity an automatic dynamic battery icon in the frontend (10%, 50%, charging, etc.) - do not add an explicit `icon:` key.

- [ ] **Step 3: Wire the new file into `configuration.yaml`**

Current end of the "Files to include" block (`home-assistant-amb/config/configuration.yaml`, lines 28-32):

```yaml
binary_sensor: !include binary_sensor.yaml
light: !include light.yaml

# Custom component config files to include
adaptive_lighting: !include adaptive_lighting.yaml
```

Change to:

```yaml
binary_sensor: !include binary_sensor.yaml
light: !include light.yaml
mqtt: !include mqtt.yaml

# Custom component config files to include
adaptive_lighting: !include adaptive_lighting.yaml
```

(One new line: `mqtt: !include mqtt.yaml`, directly after the `light:` line.)

- [ ] **Step 4: Document the new file in `CLAUDE.md`**

Current lines 56-62 of `CLAUDE.md`:

```markdown
- **Individual files included** (`!include`):
  - `input_boolean.yaml`, `input_datetime.yaml`, `input_number.yaml`: User inputs
  - `lovelace.yaml`: Dashboard index — uses `resource_mode: yaml` and registers dashboards from `dashboard/*.yaml` (overview, climate, lights, power)
  - `logbook.yaml`: Logbook configuration
  - `script.yaml`: Scripts
  - `binary_sensor.yaml`: Binary sensor definitions
  - `adaptive_lighting.yaml`: Adaptive lighting configurations for each light/room
```

Add one bullet at the end, after the `adaptive_lighting.yaml` line:

```markdown
- **Individual files included** (`!include`):
  - `input_boolean.yaml`, `input_datetime.yaml`, `input_number.yaml`: User inputs
  - `lovelace.yaml`: Dashboard index — uses `resource_mode: yaml` and registers dashboards from `dashboard/*.yaml` (overview, climate, lights, power)
  - `logbook.yaml`: Logbook configuration
  - `script.yaml`: Scripts
  - `binary_sensor.yaml`: Binary sensor definitions
  - `adaptive_lighting.yaml`: Adaptive lighting configurations for each light/room
  - `mqtt.yaml`: Manually-defined MQTT entities (currently: TeslaMate car sensors). The MQTT broker connection itself is a separate UI-managed config entry, not YAML.
```

- [ ] **Step 5: Validate**

Run from `home-assistant-amb/`:
```bash
just build && just test
```
Expected: no error output, command exits `0`. (If there is no output at all, that means it passed - `hass --script check_config` is silent on success.)

- [ ] **Step 6: Commit**

```bash
git add home-assistant-amb/config/mqtt.yaml home-assistant-amb/config/configuration.yaml CLAUDE.md
git commit -m "feat(ha): add TeslaMate battery level MQTT sensor"
```

---

### Task 2: Add a Tesla battery badge to the Overview dashboard

**Files:**
- Modify: `home-assistant-amb/config/dashboard/overview.yaml:85-93` (append one badge to the existing `badges:` list)

**Interfaces:**
- Consumes: `sensor.tesla_battery_level` (produced by Task 1).

- [ ] **Step 1: Append the badge**

Current end of the `badges:` list (`home-assistant-amb/config/dashboard/overview.yaml`, lines 85-93):

```yaml
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.climate_second_floor_temperature
        icon: mdi:home-floor-2
        name: Second Floor
        color: red
    sections:
```

Change to (insert the new badge after the `color: red` line, before `sections:`):

```yaml
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.climate_second_floor_temperature
        icon: mdi:home-floor-2
        name: Second Floor
        color: red
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.tesla_battery_level
        name: Tesla
    sections:
```

- [ ] **Step 2: Validate**

Run from `home-assistant-amb/`:
```bash
just test
```
Expected: no error output, exits `0`. Note: `check_config` validates that this file is well-formed YAML and matches the `lovelace:` integration's config schema - it does not deeply validate individual card/badge fields, so also visually confirm the badge after deploying (Task 3).

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/dashboard/overview.yaml
git commit -m "feat(ha): add Tesla battery badge to Overview dashboard"
```

---

### Task 3: Push and verify on the live Home Assistant instance

**Files:** none (deployment + manual verification task, no further code changes).

**Interfaces:**
- Consumes: `sensor.tesla_battery_level` (Task 1), Overview badge (Task 2).

- [ ] **Step 1: Push the branch**

```bash
git push -u origin feat/teslamate-battery-sensor
```
Expected: branch pushed, GitHub Actions workflow `build-and-test-ha-amb.yml` runs and passes (it runs the same `just build` / `just test` steps).

- [ ] **Step 2: Deploy to the Raspberry Pi**

This is a config-only change (no `Dockerfile` or image tag edit), so no image rebuild is needed. Tell the user to run, on the Pi, in `home-assistant-amb/`:
```bash
git fetch
git checkout feat/teslamate-battery-sensor
```
Then reload Home Assistant's YAML configuration from the UI (Developer Tools → YAML → Reload All, or Settings → System → Restart if a full restart is preferred).

- [ ] **Step 3: Verify the entity**

In Home Assistant, go to **Developer Tools → States**, filter for `sensor.tesla_battery_level`. Expected: a numeric state between `0` and `100` (matching the car's actual battery %, visible in the Tesla app or TeslaMate's own dashboard on port `3000`), not `unavailable` or `unknown`. If it shows `unavailable`, check that TeslaMate is actually connected to the car (TeslaMate UI on port `4000` should show the car as online/asleep, not erroring) - `unavailable` here specifically means the `healthy` topic reported `false`.

- [ ] **Step 4: Verify the dashboard badge**

Open the **Overview** dashboard (sidebar). Expected: a new badge labeled `Tesla` next to the floor/climate badges, showing the same percentage with a battery icon.

- [ ] **Step 5: Merge**

Once verified, open a PR from `feat/teslamate-battery-sensor` into `main` (or merge directly if that's the user's usual flow for this repo), then delete the branch.

## Exact Handoff Prompt For Builder

You are implementing a small, self-contained change to the `infra-pi-home` repo (Home Assistant config as code, managed under `home-assistant-amb/config/`). Read and follow `docs/plans/2026-07-03-teslamate-battery-sensor.md` in this repo exactly, task by task, in order. Each task has concrete file edits (exact before/after YAML shown), a validation command (`just build && just test`, run from `home-assistant-amb/`, expects silent success / exit 0), and a `git commit` step. Do not skip the branch-creation step at the start of Task 1, and do not combine or skip commits - one commit per task, using the exact commit messages given. Do not add anything beyond what the plan specifies (no extra TeslaMate sensors, no new dashboards) - the plan is intentionally minimal. If `just test` fails, fix the YAML before committing; never commit a failing config. Task 3 involves deploying to a physical Raspberry Pi and manually verifying in the Home Assistant UI - if you don't have access to that Pi/UI, complete Tasks 1 and 2 (including their commits and validation) and clearly hand off Task 3's remaining manual steps to the user instead of skipping or fabricating verification.
