# Per-Floor Window Open/Close Alerts Implementation Plan

**Source spec**: docs/specs/001-window-open-close-alerts.md

**Goal:** Push per-floor advisory notifications on hot days telling me when to close windows (outside warmer than a floor's inside) and later when to open them again (outside cools back below), at most once per direction per floor per day, with a morning "armed" confirmation.

**Architecture:** Three template binary sensors compare `sensor.openweathermap_temperature` against each floor's `sensor.climate_*_floor_temperature`. A single 08:00 "arm" automation reads today's forecast max, arms/disarms a master `input_boolean`, resets six per-floor latch booleans, and pushes the confirmation. A reusable blueprint (instantiated 3×, one per floor) reacts to the binary-sensor edges and to the arm moment, firing close/open pushes guarded by the master flag and latched per direction. Config-only change (no image rebuild).

**Tech Stack:** Home Assistant YAML (template integration, automation blueprints, input_boolean/input_number helpers), Jinja2 templates, `notify.mobile_app_j16`. Validation via `just test` (`hass --script check_config`) inside Docker.

## Global Constraints

- All config paths are relative to `home-assistant-amb/` (e.g. `config/template/window_alerts.yaml`). Commands run from the `home-assistant-amb/` directory.
- No automated logic-test harness exists. The only automated validation is `just test` (runs `hass --script check_config`); on success it prints nothing and returns exit code 0. Treat a **zero exit code with no error output** as PASS. Run `just test` immediately before every commit; do not commit or push if it fails.
- This is a **config-only** change — no `Dockerfile` or `docker-compose.yaml` edits, no image rebuild. Live deploy = checkout branch on the Pi + reload/restart via UI.
- `template/` is `!include_dir_merge_list`-merged: new files under `config/template/` must be a top-level YAML **list** (start with `- binary_sensor:` / `- sensor:`), matching `config/template/climate_floor_averages.yaml`.
- `automation/` is `!include_dir_merge_list`-merged: new files under `config/automation/` must be a top-level YAML **list** of automations.
- Notify target is `notify.mobile_app_j16` (single phone, for testing). Deep-link via nested `data.data.url: /dashboard-climate/inside-vs-outside` (dashboard id `dashboard-climate`, view path `inside-vs-outside`).
- Threshold gate default **25 °C**, tunable via `input_number.window_alert_temp_threshold`.
- Entity ids (fixed, verified): outside = `sensor.openweathermap_temperature`; inside = `sensor.climate_ground_floor_temperature`, `sensor.climate_first_floor_temperature`, `sensor.climate_second_floor_temperature`; forecast source = `sensor.weather_forecast_hourly` (its `forecast` attribute is a list of entries each with `datetime` + `temperature`).
- Attic stays excluded (already excluded from the second-floor average by design — see project `CLAUDE.md`). Do not add it.
- Do not include "Authored by Claude / Co-Authored-By Claude" trailers in commits.

---

### Task 1: Helper entities (input_boolean + input_number)
**Complexity:** Low

Adds the master arm flag, six per-floor latch booleans, and the tunable threshold. These persist across HA restarts (so already-sent alerts are not repeated) and must exist before any automation references them.

**Files:**
- Modify: `home-assistant-amb/config/input_boolean.yaml` (append 7 entries)
- Modify: `home-assistant-amb/config/input_number.yaml` (append 1 entry)

**Interfaces:**
- Consumes: nothing.
- Produces (referenced by Tasks 3, 4, 5):
  - `input_boolean.window_alert_active`
  - `input_boolean.window_close_alerted_ground`, `input_boolean.window_close_alerted_first`, `input_boolean.window_close_alerted_second`
  - `input_boolean.window_open_alerted_ground`, `input_boolean.window_open_alerted_first`, `input_boolean.window_open_alerted_second`
  - `input_number.window_alert_temp_threshold` (default 25)

- [ ] **Step 1: Append the 7 booleans to `config/input_boolean.yaml`**

Append (the file is a top-level map of `key: {name, icon, ...}`, matching existing entries like `adaptive_lighting:`):

```yaml
window_alert_active:
  name: Window Alert Active
  icon: mdi:window-closed-variant
  initial: false

window_close_alerted_ground:
  name: Window Close Alerted Ground Floor
  icon: mdi:window-closed
  initial: false

window_close_alerted_first:
  name: Window Close Alerted First Floor
  icon: mdi:window-closed
  initial: false

window_close_alerted_second:
  name: Window Close Alerted Second Floor
  icon: mdi:window-closed
  initial: false

window_open_alerted_ground:
  name: Window Open Alerted Ground Floor
  icon: mdi:window-open
  initial: false

window_open_alerted_first:
  name: Window Open Alerted First Floor
  icon: mdi:window-open
  initial: false

window_open_alerted_second:
  name: Window Open Alerted Second Floor
  icon: mdi:window-open
  initial: false
```

Note: `initial: false` matches the existing `disco_olivier` entry's style. On HA restart these keep their last state (helpers restore state); `initial` only applies when there is no prior state.

- [ ] **Step 2: Append the threshold to `config/input_number.yaml`**

Append (matching the existing `fridge_temperature_threshold` entry's exact key set — `name/initial/min/max/step/unit_of_measurement/icon`):

```yaml
window_alert_temp_threshold:
  name: Window Alert Temp Threshold
  initial: 25
  min: 20
  max: 35
  step: 0.5
  unit_of_measurement: "°C"
  icon: "mdi:thermometer-alert"
```

- [ ] **Step 3: Validate config**

Run (from `home-assistant-amb/`): `just test`
Expected: no output, exit code 0 (PASS). If it errors, fix YAML indentation/duplicate-key issues before continuing.

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/input_boolean.yaml home-assistant-amb/config/input_number.yaml
git commit -m "feat(ha): add window-alert helpers (arm flag, per-floor latches, threshold)"
```

---

### Task 2: Template binary sensors (`outside_warmer_than_*`)
**Complexity:** Low

Three template binary sensors, one per floor, each true when outside is warmer than that floor's inside average, with an availability guard so a dead sensor produces no spurious edges. These provide the on/off edges the blueprint reacts to.

**Files:**
- Create: `home-assistant-amb/config/template/window_alerts.yaml`

**Interfaces:**
- Consumes: `sensor.openweathermap_temperature`, `sensor.climate_{ground,first,second}_floor_temperature`.
- Produces (referenced by Tasks 3, 4):
  - `binary_sensor.outside_warmer_than_ground_floor`
  - `binary_sensor.outside_warmer_than_first_floor`
  - `binary_sensor.outside_warmer_than_second_floor`

- [ ] **Step 1: Create `config/template/window_alerts.yaml`**

Top-level YAML list (the `template/` dir is `!include_dir_merge_list`-merged, so the file must start with `- binary_sensor:`). The availability guard mirrors `climate_floor_averages.yaml` (`select('is_number') | list | count == 2`):

```yaml
- binary_sensor:
  - name: Outside Warmer Than Ground Floor
    unique_id: outside_warmer_than_ground_floor
    icon: mdi:sun-thermometer
    availability: >-
      {{ [
        states('sensor.openweathermap_temperature') | float(none),
        states('sensor.climate_ground_floor_temperature') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {{ states('sensor.openweathermap_temperature') | float
         > states('sensor.climate_ground_floor_temperature') | float }}

  - name: Outside Warmer Than First Floor
    unique_id: outside_warmer_than_first_floor
    icon: mdi:sun-thermometer
    availability: >-
      {{ [
        states('sensor.openweathermap_temperature') | float(none),
        states('sensor.climate_first_floor_temperature') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {{ states('sensor.openweathermap_temperature') | float
         > states('sensor.climate_first_floor_temperature') | float }}

  - name: Outside Warmer Than Second Floor
    unique_id: outside_warmer_than_second_floor
    icon: mdi:sun-thermometer
    availability: >-
      {{ [
        states('sensor.openweathermap_temperature') | float(none),
        states('sensor.climate_second_floor_temperature') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {{ states('sensor.openweathermap_temperature') | float
         > states('sensor.climate_second_floor_temperature') | float }}
```

Note: because `availability` already guarantees both inputs are numbers, the `state` template can safely use `| float` without a default.

- [ ] **Step 2: Validate config**

Run (from `home-assistant-amb/`): `just test`
Expected: no output, exit code 0 (PASS). A YAML/template syntax error will fail here.

- [ ] **Step 3: (Live template dry-run — deferred to verification)**

There is no offline template test harness. Record for the live-verification phase (Task 6): in Developer Tools → Template, paste one `state:` expression and confirm it renders `True`/`False` against live sensors, and that toggling makes sense. Not a blocker for commit.

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/template/window_alerts.yaml
git commit -m "feat(ha): add outside-warmer-than-floor template binary sensors"
```

---

### Task 3: Window-alert blueprint
**Complexity:** Medium

A reusable automation blueprint (instantiated 3× in Task 4). Reacts to a floor's `outside_warmer_than_*` edges and to the arm moment; fires close/open pushes guarded by the master flag and per-direction latches. This handles the "already hot at 08:00" case via trigger #2 (no duplicated notify logic in the arm automation).

**Files:**
- Create: `home-assistant-amb/config/blueprints/automation/custom/window_alert.yaml`

**Interfaces:**
- Consumes (from Tasks 1, 2): the floor's `binary_sensor.outside_warmer_than_*`, `input_boolean.window_alert_active`, the floor's `input_boolean.window_close_alerted_*` and `window_open_alerted_*`, the inside/outside temperature sensors, and `notify.mobile_app_j16`.
- Produces (referenced by Task 4): blueprint at path `custom/window_alert.yaml` with inputs `outside_warmer_sensor`, `floor_name`, `inside_sensor`, `outside_sensor`, `close_latch`, `open_latch`.

- [ ] **Step 1: Create `config/blueprints/automation/custom/window_alert.yaml`**

Structure mirrors `heating_needed_alert.yaml` / `water_leak.yaml` (blueprint header + `input:` + `mode` + `trigger` + `variables` + `action`). Guard on `window_alert_active == 'on'` inside the `choose`:

```yaml
blueprint:
  name: Window Open/Close Alert
  description: >
    Per-floor advisory: notify to close windows when it becomes warmer outside
    than inside, and to open them again when it cools back below. Guarded by a
    master "armed" flag and latched once-per-direction-per-day.
  domain: automation

  input:
    outside_warmer_sensor:
      name: Outside-warmer-than-floor sensor
      description: The floor's binary_sensor.outside_warmer_than_* sensor.
      selector:
        entity:
          domain: binary_sensor
    floor_name:
      name: Floor name
      description: Human readable floor name shown in notifications (e.g. "ground-floor").
      selector:
        text: {}
    inside_sensor:
      name: Inside temperature sensor
      description: The floor's average inside temperature sensor (for message text).
      selector:
        entity:
          domain: sensor
          device_class: temperature
    outside_sensor:
      name: Outside temperature sensor
      description: Outside temperature sensor (for message text).
      selector:
        entity:
          domain: sensor
          device_class: temperature
    close_latch:
      name: Close-alert latch
      description: input_boolean marking the close alert already sent today.
      selector:
        entity:
          domain: input_boolean
    open_latch:
      name: Open-alert latch
      description: input_boolean marking the open alert already sent today.
      selector:
        entity:
          domain: input_boolean

mode: restart

trigger:
  - platform: state
    entity_id: !input outside_warmer_sensor
  - platform: state
    entity_id: input_boolean.window_alert_active
    to: "on"

variables:
  outside_warmer_sensor: !input outside_warmer_sensor
  floor_name: !input floor_name
  inside_sensor: !input inside_sensor
  outside_sensor: !input outside_sensor
  close_latch: !input close_latch
  open_latch: !input open_latch

condition:
  - condition: state
    entity_id: input_boolean.window_alert_active
    state: "on"

action:
  - choose:
      - conditions:
          - condition: state
            entity_id: !input outside_warmer_sensor
            state: "on"
          - condition: state
            entity_id: !input close_latch
            state: "off"
        sequence:
          - service: notify.mobile_app_j16
            data:
              title: Windows
              message: >-
                🌡️ Close {{ floor_name }} windows — it's now warmer outside
                ({{ states(outside_sensor) | round(1) }}°) than inside
                ({{ states(inside_sensor) | round(1) }}°).
              data:
                url: /dashboard-climate/inside-vs-outside
          - service: input_boolean.turn_on
            target:
              entity_id: !input close_latch
      - conditions:
          - condition: state
            entity_id: !input outside_warmer_sensor
            state: "off"
          - condition: state
            entity_id: !input open_latch
            state: "off"
        sequence:
          - service: notify.mobile_app_j16
            data:
              title: Windows
              message: >-
                🪟 Open {{ floor_name }} windows — it's cooler outside
                ({{ states(outside_sensor) | round(1) }}°) than inside
                ({{ states(inside_sensor) | round(1) }}°) now.
              data:
                url: /dashboard-climate/inside-vs-outside
          - service: input_boolean.turn_on
            target:
              entity_id: !input open_latch
```

Notes:
- The top-level `condition:` (armed == on) covers both triggers, so a pre-arm on→off edge is suppressed (spec edge case).
- Trigger #2 (`window_alert_active` → on) covers the "already hotter outside than inside at 08:00" case: the close branch sees warmer-outside already true + latch off → immediate close alert. No separate notify logic in the arm automation.
- `notify.mobile_app_j16` with nested `data.data.url` matches the deep-link pattern in `config/automation/fridge.yaml`.

- [ ] **Step 2: Validate config**

Run (from `home-assistant-amb/`): `just test`
Expected: no output, exit code 0 (PASS). Note: `check_config` validates blueprint YAML syntax; a malformed `!input`/selector fails here. The blueprint is not exercised until instantiated (Task 4).

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/blueprints/automation/custom/window_alert.yaml
git commit -m "feat(ha): add window open/close alert blueprint"
```

---

### Task 4: Blueprint instances (3 floors)
**Complexity:** Low

Instantiates the Task 3 blueprint three times, wiring each floor's binary sensor, inside sensor, and latch booleans. This is what actually creates the running automations.

**Files:**
- Create: `home-assistant-amb/config/automation/window_alerts.yaml`

**Interfaces:**
- Consumes: blueprint `custom/window_alert.yaml` (Task 3); binary sensors (Task 2); latch booleans (Task 1).
- Produces: three automations (one per floor). No downstream consumers.

- [ ] **Step 1: Create `config/automation/window_alerts.yaml`**

Top-level YAML list of automations, each using `use_blueprint` (matching `config/automation/water_leak.yaml`'s `path:` + `input:` pattern). `path` is relative to `blueprints/automation/`:

```yaml
- alias: "Window Alert Ground Floor"
  use_blueprint:
    path: custom/window_alert.yaml
    input:
      outside_warmer_sensor: binary_sensor.outside_warmer_than_ground_floor
      floor_name: ground-floor
      inside_sensor: sensor.climate_ground_floor_temperature
      outside_sensor: sensor.openweathermap_temperature
      close_latch: input_boolean.window_close_alerted_ground
      open_latch: input_boolean.window_open_alerted_ground

- alias: "Window Alert First Floor"
  use_blueprint:
    path: custom/window_alert.yaml
    input:
      outside_warmer_sensor: binary_sensor.outside_warmer_than_first_floor
      floor_name: first-floor
      inside_sensor: sensor.climate_first_floor_temperature
      outside_sensor: sensor.openweathermap_temperature
      close_latch: input_boolean.window_close_alerted_first
      open_latch: input_boolean.window_open_alerted_first

- alias: "Window Alert Second Floor"
  use_blueprint:
    path: custom/window_alert.yaml
    input:
      outside_warmer_sensor: binary_sensor.outside_warmer_than_second_floor
      floor_name: second-floor
      inside_sensor: sensor.climate_second_floor_temperature
      outside_sensor: sensor.openweathermap_temperature
      close_latch: input_boolean.window_close_alerted_second
      open_latch: input_boolean.window_open_alerted_second
```

- [ ] **Step 2: Validate config**

Run (from `home-assistant-amb/`): `just test`
Expected: no output, exit code 0 (PASS). This is the first time the blueprint is fully resolved with its inputs; a mismatch between input names here and in Task 3, or a missing referenced entity id, surfaces now.

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/automation/window_alerts.yaml
git commit -m "feat(ha): instantiate window alert blueprint for all three floors"
```

---

### Task 5: Morning arm automation (08:00 forecast gate)
**Complexity:** Medium

A single automation (not a blueprint) that runs daily at 08:00, computes today's forecast max from `sensor.weather_forecast_hourly`, and either arms (turn on master flag, reset all 6 latches, push confirmation) or disarms (turn off master flag, no push). Turning the master flag **on** is also what triggers the blueprint's "already hot" branch.

**Files:**
- Create: `home-assistant-amb/config/automation/window_alerts_arm.yaml`

**Interfaces:**
- Consumes (from Task 1): `input_number.window_alert_temp_threshold`, `input_boolean.window_alert_active`, all 6 latch booleans. Reads `sensor.weather_forecast_hourly` `forecast` attribute. Uses `notify.mobile_app_j16`.
- Produces: no downstream consumers (turning `window_alert_active` on is observed by the Task 3 blueprint via its trigger #2).

- [ ] **Step 1: Create `config/automation/window_alerts_arm.yaml`**

Top-level YAML list with one automation. Forecast-max Jinja filters `forecast` entries to today and takes the max temperature; empty/unavailable forecast yields `none` → treated as not-hot:

```yaml
- alias: "Window Alerts Morning Arm"
  mode: single
  trigger:
    - platform: time
      at: "08:00:00"
  variables:
    threshold: "{{ states('input_number.window_alert_temp_threshold') | float(25) }}"
    forecast_max: >-
      {% set fc = state_attr('sensor.weather_forecast_hourly', 'forecast') %}
      {% if fc %}
        {% set today = fc
             | selectattr('datetime', 'defined')
             | selectattr('temperature', 'defined')
             | selectattr('datetime')
             | list %}
        {% set temps = today
             | selectattr('datetime')
             | map(attribute='datetime')
             | list %}
        {% set vals = fc
             | selectattr('temperature', 'defined')
             | selectattr('datetime', 'defined')
             | selectattr('datetime')
             | list %}
        {% set today_temps = [] %}
        {% for e in fc %}
          {% if e.datetime is defined and e.temperature is defined
                and as_local(as_datetime(e.datetime)).date() == now().date() %}
            {% set today_temps = today_temps + [e.temperature | float] %}
          {% endif %}
        {% endfor %}
        {{ today_temps | max if today_temps | count > 0 else 'none' }}
      {% else %}
        none
      {% endif %}
  action:
    - choose:
        - conditions:
            - condition: template
              value_template: >-
                {{ forecast_max != 'none'
                   and (forecast_max | float) >= (threshold | float) }}
          sequence:
            - service: input_boolean.turn_on
              target:
                entity_id: input_boolean.window_alert_active
            - service: input_boolean.turn_off
              target:
                entity_id:
                  - input_boolean.window_close_alerted_ground
                  - input_boolean.window_close_alerted_first
                  - input_boolean.window_close_alerted_second
                  - input_boolean.window_open_alerted_ground
                  - input_boolean.window_open_alerted_first
                  - input_boolean.window_open_alerted_second
            - service: notify.mobile_app_j16
              data:
                title: Windows
                message: >-
                  🪟 Window alerts armed — hot day ahead (max ~{{ forecast_max | float | round(1) }}°).
                  I'll tell you when to open/close windows per floor.
                data:
                  url: /dashboard-climate/inside-vs-outside
      default:
        - service: input_boolean.turn_off
          target:
            entity_id: input_boolean.window_alert_active
```

Notes:
- Latches are reset **before** `window_alert_active` observation matters; but the blueprint's trigger #2 fires on `window_alert_active` → on. Since `turn_on` of the master flag is the first action and the latch reset is the second, there is a possible race where the blueprint's immediate-close branch reads a latch still `on` from yesterday. **Ordering fix (important): reset the 6 latches FIRST, then turn on `window_alert_active` LAST**, so the blueprint's trigger #2 sees freshly-reset latches. Reorder the two service calls accordingly in the `sequence` (latch `turn_off` block first, `window_alert_active` `turn_on` second, then the notify).
- The `variables` block above contains redundant intermediate sets (`temps`, `vals`, `today`) left from iteration — **delete those; keep only the `fc` guard, the `today_temps` loop, and the final `{{ today_temps | max ... }}`**. Final minimal `forecast_max`:

```yaml
    forecast_max: >-
      {% set fc = state_attr('sensor.weather_forecast_hourly', 'forecast') %}
      {% if fc %}
        {% set ns = namespace(temps=[]) %}
        {% for e in fc %}
          {% if e.datetime is defined and e.temperature is defined
                and as_local(as_datetime(e.datetime)).date() == now().date() %}
            {% set ns.temps = ns.temps + [e.temperature | float] %}
          {% endif %}
        {% endfor %}
        {{ ns.temps | max if ns.temps | count > 0 else 'none' }}
      {% else %}
        none
      {% endif %}
```

Use this minimal `forecast_max` (Jinja loops need `namespace` to accumulate across iterations — plain `{% set %}` inside a `for` does not persist). And apply the latch-first ordering. Final `action` sequence order for the arm branch:
1. `input_boolean.turn_off` the 6 latches
2. `input_boolean.turn_on` `window_alert_active`
3. `notify.mobile_app_j16` confirmation

- [ ] **Step 2: Validate config**

Run (from `home-assistant-amb/`): `just test`
Expected: no output, exit code 0 (PASS). Catches Jinja syntax errors in the `forecast_max` template and any malformed service target.

- [ ] **Step 3: (Live template dry-run — deferred to verification)**

Record for Task 6: paste the `forecast_max` template into Developer Tools → Template against live `sensor.weather_forecast_hourly` and confirm it returns a plausible number (today's max) or `none`. Not a commit blocker.

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/automation/window_alerts_arm.yaml
git commit -m "feat(ha): add 08:00 forecast-gated window-alert arm automation"
```

---

### Task 6: Live verification on the Pi
**Complexity:** Low

No code changes — this is the manual verification pass the repo relies on in place of an automation-logic test harness. Do it after the branch is pushed and CI is green.

**Files:** none (verification only).

**Interfaces:**
- Consumes: everything from Tasks 1–5 deployed to the live instance.
- Produces: confirmation the feature behaves per spec.

- [ ] **Step 1: Deploy to the Pi**

On the Raspberry Pi, in `home-assistant-amb/`: checkout the branch (or `git pull` if iterating). Image is unchanged, so **no rebuild** — reload/restart via UI. New `input_boolean`/`input_number` helpers require a **restart** (or reload of the specific helper domains) to register.

- [ ] **Step 2: Template sanity (Developer Tools → Template)**

Paste the `forecast_max` template from Task 5 → confirm it returns today's forecast max (a number) or `none`. Paste one `outside_warmer_than_*` `state:` expression → confirm `True`/`False` matches reality.
Expected: sensible values; no template errors.

- [ ] **Step 3: Arm path**

Lower `input_number.window_alert_temp_threshold` below the current forecast max, then manually run the "Window Alerts Morning Arm" automation.
Expected: "🪟 Window alerts armed" push received; `input_boolean.window_alert_active` = on; all 6 latch booleans = off.

- [ ] **Step 4: Close alert + no-repeat**

While armed, drive a floor's `binary_sensor.outside_warmer_than_*` to `on` (e.g. temporarily set threshold/inputs, or use Developer Tools → States to override the source sensors so the template flips).
Expected: exactly one "🌡️ Close …" push for that floor; its `window_close_alerted_*` latch = on. Re-toggle the sensor on↔off → confirm **no repeat** close push.

- [ ] **Step 5: Open alert**

Flip that floor's binary sensor back to `off`.
Expected: one "🪟 Open …" push; `window_open_alerted_*` latch = on; no repeat on further toggles.

- [ ] **Step 6: Already-hot-at-08:00**

Arrange a floor to be already warmer-outside (binary sensor already `on`), reset that floor's close latch to off, then run the arm automation.
Expected: immediate "🌡️ Close …" push for that floor (via blueprint trigger #2), no off→on edge required.

- [ ] **Step 7: Non-hot day**

Raise `window_alert_temp_threshold` above the current forecast max and run the arm automation.
Expected: no push; `window_alert_active` = off; toggling any `outside_warmer_than_*` fires no alerts (blueprint condition gates on armed).

- [ ] **Step 8: Restore + document**

Restore `window_alert_temp_threshold` to 25 and clear any manual state overrides. No commit needed unless a bug was found (then fix in the relevant task's file, re-run `just test`, commit).

---

## Task Dependency Summary

- **Task 1** (helpers) — no deps. Do first.
- **Task 2** (template sensors) — no deps. Independent of Task 1.
- **Task 3** (blueprint) — references helpers (Task 1) and sensors (Task 2) by id in text, but `check_config` validates it standalone; logically depends on 1 & 2 for live behavior.
- **Task 4** (instances) — depends on **Task 3** (blueprint must exist) and references entities from **Tasks 1 & 2**. `just test` will fail if the blueprint path/inputs don't resolve.
- **Task 5** (arm automation) — depends on **Task 1** (helpers). Independent of 2/3/4 for validation.
- **Task 6** (live verification) — depends on **all** of 1–5 deployed.

Recommended order: 1 → 2 → 3 → 4 → 5 → 6.

## Deployment

Config-only. Per project `CLAUDE.md`: create a branch, run `just test`, commit per task, push (CI re-validates on `home-assistant-amb/**`). Then on the Pi checkout the branch and reload/restart via UI. Helpers in `input_boolean.yaml`/`input_number.yaml` require a restart (or reload of those helper domains) to register. Do the live verification (Task 6) before considering the feature done.
