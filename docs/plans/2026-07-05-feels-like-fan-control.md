# Feels-Like Fan Control Implementation Plan

**Goal:** Study and Bedroom JC fans ramp up based on "feels like" (apparent) temperature instead of raw air temperature, and the Fans dashboard shows both values.

**Architecture:** Add two new template sensors (one per room) that combine each room's existing temperature + humidity Zigbee sensors into a "feels like" value using a simplified apparent-temperature formula. Point the existing fan-speed-ramp automations and their duplicate dashboard-button scripts at the new sensors instead of raw temperature. Relabel the on-dashboard settings that define the ramp thresholds so it's clear they now compare against feels-like. Add two new charts to the Fans dashboard (one per room) plotting actual vs. feels-like temperature, and swap the dashboard's top-of-view badges to show feels-like.

**Tech Stack:** Home Assistant YAML configuration (template sensors, automations, scripts, Lovelace dashboard), Jinja2 templating, the `custom:apexcharts-card` Lovelace card (already loaded in this repo's image), Docker (`hass --script check_config` via `just test`).

## Global Constraints

- Home Assistant version pinned: `ghcr.io/home-assistant/home-assistant:2026.5.2` (see `home-assistant-amb/Dockerfile`) - no config feature beyond this version.
- YAML indentation: 2 spaces, matching all existing files in `home-assistant-amb/config/`.
- Run `just test` from the `home-assistant-amb/` directory before every commit. If there are no problems, there is **no output** and exit code is `0` - that counts as a pass, not a failure. If it fails because no local Docker image exists yet, run `just build` first, then `just test` again.
- Run `pre-commit run --all-files` from the repo root before the final push (hooks: `check-yaml`, `end-of-file-fixer`, `trailing-whitespace`).
- Confirmed feels-like formula: the Australian Bureau of Meteorology's simplified apparent temperature, with the wind-speed term dropped (no wind indoors):
  - `vp = (RH / 100) * 6.105 * e^(17.27 * T / (237.7 + T))` (vapor pressure, hPa)
  - `feels_like = T + 0.33 * vp - 4.0`, rounded to 1 decimal
  - `e^x` is written in Jinja2 as `2.718281828459045 ** x` (Jinja2 has no `exp` filter but supports the `**` power operator natively).
- Confirmed new entity IDs: `sensor.climate_study_feels_like_temperature`, `sensor.climate_bedroom_jc_feels_like_temperature`, defined in a new file `home-assistant-amb/config/template/climate_feels_like.yaml`.
- Confirmed fan control change: `automation/fan_study.yaml`, `automation/fan_bedroom_jc.yaml`, and the `fan_study_turn_on`/`fan_bedroom_jc_turn_on` scripts in `script.yaml` all switch from raw temperature to the new feels-like sensors. If a feels-like sensor is ever unavailable, the existing `| float(0)` default kicks in (same as today) and the fan stays off - no new fallback logic.
- Confirmed relabeling: the 4 existing `input_number` friendly names and their matching dashboard tile name overrides (Start Temp / End Temp, for both rooms) change to say "Feels Like" (e.g. "Fan Study Start Temp" → "Fan Study Start Feels Like Temp"). The fan-speed-curve chart's title and x-axis title on the dashboard also change to say "feels-like". Entity IDs are unchanged - only display text changes.
- Confirmed badges: the 2 top-of-view badges on the Fans dashboard ("Study", "Bedroom JC") swap their entity from raw temperature to feels-like temperature entirely (not additive - still exactly 1 badge per room). Name/icon/color unchanged.
- Confirmed chart design: 2 new `custom:apexcharts-card` cards on the Fans dashboard, one per room, placed directly under that room's fan tiles. Each shows actual temperature (solid line, opacity 0.9) and feels-like temperature (dashed line via `stroke_dash: 4`, opacity 0.6), same color per room, last 24h ending now. Study color `#009688` (teal), Bedroom JC color `#f44336` (red) - matches this repo's existing badge/plotly colors for these rooms.
- Out of scope, do not touch: `automation/heating_needed_alert.yaml`, `template/climate_floor_averages.yaml`, and the "Measurements per room" / "Measurements per floor" dashboard views. They keep using raw actual temperature.

---

### Task 1: Add feels-like temperature sensors

**Files:**
- Create: `home-assistant-amb/config/template/climate_feels_like.yaml`

**Interfaces:**
- Consumes: `sensor.climate_study_temperature`, `sensor.climate_study_humidity`, `sensor.climate_bedroom_jc_temperature`, `sensor.climate_bedroom_jc_humidity` (existing Zigbee2MQTT sensors, already used in `template/climate_floor_averages.yaml`).
- Produces: `sensor.climate_study_feels_like_temperature` and `sensor.climate_bedroom_jc_feels_like_temperature` - both numeric, unit `°C`, `device_class: temperature`. Used by Task 2 (automations/scripts) and Task 4 (dashboard).

- [ ] **Step 1: Create the template sensor file**

Create `home-assistant-amb/config/template/climate_feels_like.yaml` (this new file is automatically picked up - `configuration.yaml` already merges everything under `template/` via `!include_dir_merge_list template/`, no registration needed):

```yaml
- sensor:
  # "Feels like" temperature blends air temperature with humidity into a single
  # apparent-temperature value: at the same air temperature, higher humidity feels
  # warmer, lower humidity feels cooler. Formula: the Australian Bureau of
  # Meteorology's simplified apparent temperature, with the wind-speed term
  # dropped (there is no wind indoors).
  #   vp = (RH / 100) * 6.105 * e^(17.27 * T / (237.7 + T))   -- vapor pressure (hPa)
  #   feels_like = T + 0.33 * vp - 4.0
  # e^x is written as `2.718281828459045 ** x` - Jinja2 has no `exp` filter, but
  # supports the `**` power operator natively.
  - name: Climate Study Feels Like Temperature
    unique_id: climate_study_feels_like_temperature
    unit_of_measurement: °C
    device_class: temperature
    state_class: measurement
    availability: >-
      {{ [
        states('sensor.climate_study_temperature') | float(none),
        states('sensor.climate_study_humidity') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {% set t = states('sensor.climate_study_temperature') | float(0) %}
      {% set rh = states('sensor.climate_study_humidity') | float(0) %}
      {% set vp = (rh / 100) * 6.105 * (2.718281828459045 ** (17.27 * t / (237.7 + t))) %}
      {{ (t + 0.33 * vp - 4.0) | round(1) }}

  - name: Climate Bedroom JC Feels Like Temperature
    unique_id: climate_bedroom_jc_feels_like_temperature
    unit_of_measurement: °C
    device_class: temperature
    state_class: measurement
    availability: >-
      {{ [
        states('sensor.climate_bedroom_jc_temperature') | float(none),
        states('sensor.climate_bedroom_jc_humidity') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {% set t = states('sensor.climate_bedroom_jc_temperature') | float(0) %}
      {% set rh = states('sensor.climate_bedroom_jc_humidity') | float(0) %}
      {% set vp = (rh / 100) * 6.105 * (2.718281828459045 ** (17.27 * t / (237.7 + t))) %}
      {{ (t + 0.33 * vp - 4.0) | round(1) }}
```

The `availability:` guard mirrors the pattern already used in `template/climate_floor_averages.yaml`: if either the temperature or humidity sensor is unavailable/non-numeric, this sensor reports `unavailable` instead of a misleading fake value.

- [ ] **Step 2: Sanity-check the formula in plain Python**

Before trusting this inside Jinja, verify the arithmetic behaves sensibly (feels-like should read a few degrees *above* actual at high humidity, and can read slightly *below* actual at low humidity - both are correct behavior for this formula, not a bug):

```bash
python3 -c "
def feels_like(t, rh):
    vp = (rh/100) * 6.105 * (2.718281828459045 ** (17.27*t/(237.7+t)))
    return round(t + 0.33*vp - 4.0, 1)

print('28C/60%RH ->', feels_like(28.0, 60.0))
print('22C/45%RH ->', feels_like(22.0, 45.0))
"
```

Expected output:
```
28C/60%RH -> 31.5
22C/45%RH -> 21.9
```

- [ ] **Step 3: Validate Home Assistant config**

```bash
cd home-assistant-amb
just test
```

Expected: no output, exit code `0`.

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/template/climate_feels_like.yaml
git commit -m "feat(ha): add feels-like temperature sensors for study and bedroom jc"
```

---

### Task 2: Drive the fans from feels-like temperature

**Files:**
- Modify: `home-assistant-amb/config/automation/fan_study.yaml:9`
- Modify: `home-assistant-amb/config/automation/fan_bedroom_jc.yaml:8`
- Modify: `home-assistant-amb/config/script.yaml:69` and `:91`

**Interfaces:**
- Consumes: `sensor.climate_study_feels_like_temperature`, `sensor.climate_bedroom_jc_feels_like_temperature` (Task 1).
- Produces: none - this only changes which sensor the existing ramp calculation reads from. The ramp math itself, the `input_number` thresholds it reads, and the `fan.set_percentage` call are unchanged.

- [ ] **Step 1: Update the "Fan study on" automation**

In `home-assistant-amb/config/automation/fan_study.yaml`, find:

```yaml
    target_pct: >
      {% set t = states('sensor.climate_study_temperature') | float(0) %}
```

Replace the `t` line only:

```yaml
    target_pct: >
      {% set t = states('sensor.climate_study_feels_like_temperature') | float(0) %}
```

- [ ] **Step 2: Update the "Fan Bedroom JC on" automation**

In `home-assistant-amb/config/automation/fan_bedroom_jc.yaml`, find:

```yaml
    target_pct: >
      {% set t = states('sensor.climate_bedroom_jc_temperature') | float(0) %}
```

Replace the `t` line only:

```yaml
    target_pct: >
      {% set t = states('sensor.climate_bedroom_jc_feels_like_temperature') | float(0) %}
```

- [ ] **Step 3: Update the "Turn on at calculated speed" scripts**

In `home-assistant-amb/config/script.yaml`, the dashboard's manual "Turn On at Calculated Speed" buttons call these scripts, which duplicate the same ramp calculation. Find (inside `fan_study_turn_on`):

```yaml
        target_pct: >
          {% set t = states('sensor.climate_study_temperature') | float(0) %}
```

Replace the `t` line only:

```yaml
        target_pct: >
          {% set t = states('sensor.climate_study_feels_like_temperature') | float(0) %}
```

Find (inside `fan_bedroom_jc_turn_on`, further down the same file):

```yaml
        target_pct: >
          {% set t = states('sensor.climate_bedroom_jc_temperature') | float(0) %}
```

Replace the `t` line only:

```yaml
        target_pct: >
          {% set t = states('sensor.climate_bedroom_jc_feels_like_temperature') | float(0) %}
```

- [ ] **Step 4: Confirm no raw-temperature references remain in these files**

```bash
grep -n "climate_study_temperature\|climate_bedroom_jc_temperature" \
  home-assistant-amb/config/automation/fan_study.yaml \
  home-assistant-amb/config/automation/fan_bedroom_jc.yaml \
  home-assistant-amb/config/script.yaml
```

Expected: no output (all 4 occurrences across these 3 files were replaced with the `_feels_like_` variants).

- [ ] **Step 5: Validate Home Assistant config**

```bash
cd home-assistant-amb
just test
```

Expected: no output, exit code `0`.

- [ ] **Step 6: Commit**

```bash
git add home-assistant-amb/config/automation/fan_study.yaml \
  home-assistant-amb/config/automation/fan_bedroom_jc.yaml \
  home-assistant-amb/config/script.yaml
git commit -m "feat(ha): drive study and bedroom jc fans from feels-like temperature"
```

---

### Task 3: Relabel the fan threshold settings

**Files:**
- Modify: `home-assistant-amb/config/input_number.yaml:36-79`
- Modify: `home-assistant-amb/config/dashboard/climate.yaml` (Settings section tile names + fan-speed-curve chart titles)

**Interfaces:**
- Consumes: none new.
- Produces: none - display text only, entity IDs (`input_number.fan_study_start_temp`, `input_number.fan_study_end_temp`, `input_number.fan_bedroom_jc_start_temp`, `input_number.fan_bedroom_jc_end_temp`) are unchanged, so nothing else in the config needs updating.

- [ ] **Step 1: Rename the `input_number` helpers' friendly names**

In `home-assistant-amb/config/input_number.yaml`, update these 4 `name:` fields (leave `initial`/`min`/`max`/`step`/`unit_of_measurement`/`icon` untouched):

Find:
```yaml
fan_study_start_temp:
  name: Fan Study Start Temp
```
Replace with:
```yaml
fan_study_start_temp:
  name: Fan Study Start Feels Like Temp
```

Find:
```yaml
fan_study_end_temp:
  name: Fan Study End Temp
```
Replace with:
```yaml
fan_study_end_temp:
  name: Fan Study End Feels Like Temp
```

Find:
```yaml
fan_bedroom_jc_start_temp:
  name: Fan Bedroom JC Start Temp
```
Replace with:
```yaml
fan_bedroom_jc_start_temp:
  name: Fan Bedroom JC Start Feels Like Temp
```

Find:
```yaml
fan_bedroom_jc_end_temp:
  name: Fan Bedroom JC End Temp
```
Replace with:
```yaml
fan_bedroom_jc_end_temp:
  name: Fan Bedroom JC End Feels Like Temp
```

(`fan_study_end_pct` and `fan_bedroom_jc_end_pct` don't mention "Temp" - leave both unchanged.)

- [ ] **Step 2: Rename the matching dashboard tile labels**

In `home-assistant-amb/config/dashboard/climate.yaml`, in the "Fans" view's "Settings" section, find the Study horizontal-stack:

```yaml
              - type: tile
                entity: input_number.fan_study_start_temp
                name: Start Temp
                features:
                  - type: numeric-input
                    style: buttons
              - type: tile
                entity: input_number.fan_study_end_temp
                name: End Temp
                features:
                  - type: numeric-input
                    style: buttons
```

Replace with:

```yaml
              - type: tile
                entity: input_number.fan_study_start_temp
                name: Start Feels Like Temp
                features:
                  - type: numeric-input
                    style: buttons
              - type: tile
                entity: input_number.fan_study_end_temp
                name: End Feels Like Temp
                features:
                  - type: numeric-input
                    style: buttons
```

Then find the Bedroom JC horizontal-stack further down:

```yaml
              - type: tile
                entity: input_number.fan_bedroom_jc_start_temp
                name: Start Temp
                features:
                  - type: numeric-input
                    style: buttons
              - type: tile
                entity: input_number.fan_bedroom_jc_end_temp
                name: End Temp
                features:
                  - type: numeric-input
                    style: buttons
```

Replace with:

```yaml
              - type: tile
                entity: input_number.fan_bedroom_jc_start_temp
                name: Start Feels Like Temp
                features:
                  - type: numeric-input
                    style: buttons
              - type: tile
                entity: input_number.fan_bedroom_jc_end_temp
                name: End Feels Like Temp
                features:
                  - type: numeric-input
                    style: buttons
```

- [ ] **Step 3: Relabel the fan-speed-curve chart**

In the same file, in the `custom:plotly-graph` card, find:

```yaml
            title: Desired fan speed vs temperature
```

Replace with:

```yaml
            title: Desired fan speed vs feels-like temperature
```

A few lines below, find:

```yaml
              xaxis:
                title: "Temperature (°C)"
```

Replace with:

```yaml
              xaxis:
                title: "Feels Like Temperature (°C)"
```

- [ ] **Step 4: Validate Home Assistant config**

```bash
cd home-assistant-amb
just test
```

Expected: no output, exit code `0`.

- [ ] **Step 5: Commit**

```bash
git add home-assistant-amb/config/input_number.yaml home-assistant-amb/config/dashboard/climate.yaml
git commit -m "feat(ha): relabel fan temp settings as feels-like"
```

---

### Task 4: Show feels-like temperature on the Fans dashboard

**Files:**
- Modify: `home-assistant-amb/config/dashboard/climate.yaml` (Fans view: top badges + 2 new chart cards)

**Interfaces:**
- Consumes: `sensor.climate_study_temperature`, `sensor.climate_study_feels_like_temperature`, `sensor.climate_bedroom_jc_temperature`, `sensor.climate_bedroom_jc_feels_like_temperature` (Task 1 for the `_feels_like_` ones).
- Produces: none - dashboard-only change.

- [ ] **Step 1: Swap the top badges to feels-like**

In `home-assistant-amb/config/dashboard/climate.yaml`, in the "Fans" view's `badges:` block, find:

```yaml
    badges:
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.climate_study_temperature
        name: Study
        icon: mdi:chair-rolling
        color: teal
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.climate_bedroom_jc_temperature
        name: Bedroom JC
        icon: mdi:bed
        color: red
```

Replace with:

```yaml
    badges:
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.climate_study_feels_like_temperature
        name: Study
        icon: mdi:chair-rolling
        color: teal
      - type: entity
        show_name: true
        show_state: true
        show_icon: true
        entity: sensor.climate_bedroom_jc_feels_like_temperature
        name: Bedroom JC
        icon: mdi:bed
        color: red
```

- [ ] **Step 2: Add the Study temperature chart**

In the same file, in the "Fans" grid section (first `sections:` entry of the Fans view), find the end of the Study block:

```yaml
          - type: tile
            entity: script.fan_study_turn_on
            name: Turn On at Calculated Speed
            icon: mdi:fan-auto
            hide_state: true
            tap_action:
              action: call-service
              service: script.fan_study_turn_on
          - type: heading
            heading: Bedroom JC
            heading_style: subtitle
            icon: mdi:bed
```

Insert a new chart card between the tile and the "Bedroom JC" heading:

```yaml
          - type: tile
            entity: script.fan_study_turn_on
            name: Turn On at Calculated Speed
            icon: mdi:fan-auto
            hide_state: true
            tap_action:
              action: call-service
              service: script.fan_study_turn_on
          - type: custom:apexcharts-card
            grid_options:
              columns: full
            apex_config:
              chart:
                height: 200px
            header:
              show: true
              title: Study temperature
              show_states: true
              colorize_states: true
            graph_span: 24h
            hours_12: false
            all_series_config:
              stroke_width: 3
            series:
              - entity: sensor.climate_study_temperature
                name: Actual
                extend_to: now
                color: "#009688"
                opacity: 0.9
                type: line
              - entity: sensor.climate_study_feels_like_temperature
                name: Feels like
                extend_to: now
                color: "#009688"
                opacity: 0.6
                stroke_dash: 4
                type: line
          - type: heading
            heading: Bedroom JC
            heading_style: subtitle
            icon: mdi:bed
```

- [ ] **Step 3: Add the Bedroom JC temperature chart**

Further down in the same grid section, find the end of the Bedroom JC block (right before the second `sections:` entry, "Settings", begins):

```yaml
          - type: tile
            entity: script.fan_bedroom_jc_turn_on
            name: Turn On at Calculated Speed
            icon: mdi:fan-auto
            hide_state: true
            tap_action:
              action: call-service
              service: script.fan_bedroom_jc_turn_on
      - type: grid
        cards:
          - type: heading
            heading: Settings
```

Insert a new chart card between the tile and the `- type: grid` line (which starts the "Settings" section - keep that line and everything after it exactly as-is):

```yaml
          - type: tile
            entity: script.fan_bedroom_jc_turn_on
            name: Turn On at Calculated Speed
            icon: mdi:fan-auto
            hide_state: true
            tap_action:
              action: call-service
              service: script.fan_bedroom_jc_turn_on
          - type: custom:apexcharts-card
            grid_options:
              columns: full
            apex_config:
              chart:
                height: 200px
            header:
              show: true
              title: Bedroom JC temperature
              show_states: true
              colorize_states: true
            graph_span: 24h
            hours_12: false
            all_series_config:
              stroke_width: 3
            series:
              - entity: sensor.climate_bedroom_jc_temperature
                name: Actual
                extend_to: now
                color: "#f44336"
                opacity: 0.9
                type: line
              - entity: sensor.climate_bedroom_jc_feels_like_temperature
                name: Feels like
                extend_to: now
                color: "#f44336"
                opacity: 0.6
                stroke_dash: 4
                type: line
      - type: grid
        cards:
          - type: heading
            heading: Settings
```

- [ ] **Step 4: Validate Home Assistant config**

```bash
cd home-assistant-amb
just test
```

Expected: no output, exit code `0`.

- [ ] **Step 5: Commit**

```bash
git add home-assistant-amb/config/dashboard/climate.yaml
git commit -m "feat(ha): show feels-like temperature on fans dashboard"
```

---

### Task 5: Deploy and verify on live Home Assistant

**Files:** None - this task deploys and verifies the changes from Tasks 1-4. No config is changed.

**Interfaces:** N/A (verification task).

- [ ] **Step 1: Final local validation**

From the repo root:

```bash
pre-commit run --all-files
```

Expected: all hooks pass (`check-yaml`, `end-of-file-fixer`, `trailing-whitespace`). If a hook auto-fixes a file (e.g. adds a missing trailing newline), stage and commit the fix:

```bash
git add -A
git commit -m "chore: fix pre-commit formatting"
```

- [ ] **Step 2: Push and open a PR**

```bash
git push -u origin HEAD
gh pr create --fill
```

CI runs the same `just test` config validation on push - confirm it passes before merging.

- [ ] **Step 3: Deploy to the Raspberry Pi**

The Docker image is unchanged (only YAML config changed, not the Dockerfile or the image tag in `docker-compose.yaml`). On the Pi, in the `home-assistant-amb` directory:

```bash
git pull
```

Then in the Home Assistant UI, go to **Developer Tools → YAML** and reload **Template Entities**, **Automations**, **Scripts**, and **Helpers** (or do a full **Settings → System → Restart** if simpler - either picks up the new sensors, the 2 changed automations, the 2 changed scripts, and the relabeled helpers).

- [ ] **Step 4: Verify the new feels-like sensors**

In the Home Assistant UI, go to **Developer Tools → States**. Find `sensor.climate_study_feels_like_temperature` and `sensor.climate_bedroom_jc_feels_like_temperature`. Confirm both:
- Show a numeric `°C` value (not `unavailable` or `unknown`).
- Are within a few degrees of that room's actual temperature (`sensor.climate_study_temperature` / `sensor.climate_bedroom_jc_temperature`) - a bit *above* actual if humidity is currently high, a bit *below* if humidity is currently low. Both directions are expected (see the formula comment in `template/climate_feels_like.yaml`).

- [ ] **Step 5: Verify the dashboard**

Open the Fans dashboard (Climate → Fans view):
- The top "Study" and "Bedroom JC" badges now show the feels-like values noted in Step 4.
- Two new charts appear: "Study temperature" (under the Study tiles) and "Bedroom JC temperature" (under the Bedroom JC tiles), each with a solid "Actual" line and a dashed "Feels like" line. The feels-like line only has data starting from when you reloaded config in Step 3 - a short/flat line at first is expected, not a bug.
- In the Settings section, the Study and Bedroom JC tiles read "Start Feels Like Temp" / "End Feels Like Temp", and the fan-speed-curve chart title reads "Desired fan speed vs feels-like temperature" with x-axis "Feels Like Temperature (°C)".

- [ ] **Step 6: Verify the fans respond to feels-like thresholds end-to-end**

Pick one room (e.g. Study). In **Developer Tools → States**:
1. Note the current value of `sensor.climate_study_feels_like_temperature` - call it `F0`. Note the current values of `input_number.fan_study_start_temp` and `input_number.fan_study_end_temp` so you can restore them afterward.
2. Use **Set State** (or the Settings tile on the dashboard) to temporarily set `input_number.fan_study_start_temp` to `F0 - 2` and `input_number.fan_study_end_temp` to `F0 + 3` - this brackets the current feels-like reading so the ramp should produce a nonzero speed.
3. On the Fans dashboard, tap the Study "Turn On at Calculated Speed" tile (or in **Developer Tools → Actions**, call `script.fan_study_turn_on`).
4. Confirm `fan.fan_study`'s speed (the fan-speed tile, or its `percentage` attribute in Developer Tools → States) changed to a nonzero value.
5. Restore `input_number.fan_study_start_temp` and `input_number.fan_study_end_temp` to the values you noted in step 1.
