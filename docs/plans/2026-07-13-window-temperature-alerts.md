# Window Temperature Alerts per Floor Implementation Plan

**Source spec**: `docs/specs/001-window-temperature-alerts.md`

**Goal:** Send J16 one-time per-floor window close/open guidance on forecast-hot days.

**Architecture:** Add unavailable-safe comparison template sensors plus restored helpers for daily activation and delivery state. A single blueprint handles stable crossover detection and notifications for a floor; one scheduled automation calculates the local-day forecast maximum and instantiates that blueprint three times.

**Tech Stack:** Home Assistant 2026.7.0 YAML configuration, Jinja2 templates, Home Assistant automation blueprints, OpenWeatherMap forecast data, mobile-app notifications.

## Global Constraints

- Activation runs exactly at `08:00` local time. No startup or late retry is permitted.
- Qualify only when highest valid *future* hourly forecast entry whose local date is today is strictly greater than `25°C`.
- Use `sensor.openweathermap_temperature`, `sensor.weather_forecast_hourly`, and existing ground/first/second floor average sensors. Do not alter dashboard/chart/floor-average definitions or add attic.
- Comparison sensors must be `unavailable` unless both temperatures are numeric. Never default a missing temperature to zero.
- Keep activation and six sent flags persistent across restarts. Do not set `initial` on sent flags.
- Every close/open relation requires five uninterrupted minutes; an initial cooler relation must not create an open alert.
- Each qualifying day permits one activation, at most one close, and at most one open notification per floor. Close and open flags are independent.
- Notification target is `notify.mobile_app_j16`; notification data URL is `/dashboard-climate/inside-vs-outside`.
- YAML uses two-space indentation. Run `just test` from `home-assistant-amb` and `pre-commit run --all-files` from repository root.

---

## File Structure

| File | Responsibility |
|---|---|
| `home-assistant-amb/config/template/window_heat_alerts.yaml` | Derive `warmer`, `equal`, or `cooler` per floor only from valid numeric values. |
| `home-assistant-amb/config/input_datetime.yaml` | Persist date making guidance active. |
| `home-assistant-amb/config/input_boolean.yaml` | Persist independent per-floor close/open delivery flags. |
| `home-assistant-amb/config/blueprints/automation/custom/window_heat_alert.yaml` | Reusable floor-level five-minute crossover, activation reconciliation, notification, and one-shot behavior. |
| `home-assistant-amb/config/automation/window_heat_alerts.yaml` | 08:00 forecast evaluation and three blueprint instances. |

No automated Home Assistant YAML unit-test harness exists in this repository. Each task uses `just test` for schema/config validation; final task executes exact manual behavior matrix from source spec.

### Task 1: Add comparison sensors and persistent state
**Complexity:** Medium

**Files:**
- Create: `home-assistant-amb/config/template/window_heat_alerts.yaml`
- Modify: `home-assistant-amb/config/input_datetime.yaml`
- Modify: `home-assistant-amb/config/input_boolean.yaml`

**Interfaces:**
- Consumes: `sensor.openweathermap_temperature`; `sensor.climate_{ground,first,second}_floor_temperature`.
- Produces: `sensor.window_heat_{ground,first,second}_floor_comparison` with state `warmer|equal|cooler|unavailable`; `input_datetime.window_heat_alert_activation_date`; six `input_boolean.window_heat_*_{close,open}_sent` helpers.

- [ ] **Step 1: Create unavailable-safe comparison sensors**

Create `home-assistant-amb/config/template/window_heat_alerts.yaml`:

```yaml
- sensor:
  - name: Window Heat Ground Floor Comparison
    unique_id: window_heat_ground_floor_comparison
    availability: >-
      {{ [
        states('sensor.openweathermap_temperature') | float(none),
        states('sensor.climate_ground_floor_temperature') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {% set outside = states('sensor.openweathermap_temperature') | float(none) %}
      {% set inside = states('sensor.climate_ground_floor_temperature') | float(none) %}
      {% if outside > inside %}warmer{% elif outside < inside %}cooler{% else %}equal{% endif %}

  - name: Window Heat First Floor Comparison
    unique_id: window_heat_first_floor_comparison
    availability: >-
      {{ [
        states('sensor.openweathermap_temperature') | float(none),
        states('sensor.climate_first_floor_temperature') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {% set outside = states('sensor.openweathermap_temperature') | float(none) %}
      {% set inside = states('sensor.climate_first_floor_temperature') | float(none) %}
      {% if outside > inside %}warmer{% elif outside < inside %}cooler{% else %}equal{% endif %}

  - name: Window Heat Second Floor Comparison
    unique_id: window_heat_second_floor_comparison
    availability: >-
      {{ [
        states('sensor.openweathermap_temperature') | float(none),
        states('sensor.climate_second_floor_temperature') | float(none)
      ] | select('is_number') | list | count == 2 }}
    state: >-
      {% set outside = states('sensor.openweathermap_temperature') | float(none) %}
      {% set inside = states('sensor.climate_second_floor_temperature') | float(none) %}
      {% if outside > inside %}warmer{% elif outside < inside %}cooler{% else %}equal{% endif %}
```

- [ ] **Step 2: Add restored helpers**

Append to `home-assistant-amb/config/input_datetime.yaml`:

```yaml
window_heat_alert_activation_date:
  name: Window Heat Alert Activation Date
  has_date: true
  has_time: false
```

Append to `home-assistant-amb/config/input_boolean.yaml`. Do not add `initial` to any of these:

```yaml
window_heat_ground_floor_close_sent:
  name: Window Heat Ground Floor Close Sent
window_heat_ground_floor_open_sent:
  name: Window Heat Ground Floor Open Sent
window_heat_first_floor_close_sent:
  name: Window Heat First Floor Close Sent
window_heat_first_floor_open_sent:
  name: Window Heat First Floor Open Sent
window_heat_second_floor_close_sent:
  name: Window Heat Second Floor Close Sent
window_heat_second_floor_open_sent:
  name: Window Heat Second Floor Open Sent
```

- [ ] **Step 3: Validate configuration**

Run: `cd home-assistant-amb && just test`

Expected: no output and exit code `0`.

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/template/window_heat_alerts.yaml \
  home-assistant-amb/config/input_datetime.yaml \
  home-assistant-amb/config/input_boolean.yaml
git commit -m "feat(ha): add window heat alert state"
```

### Task 2: Create reusable per-floor alert blueprint
**Complexity:** Medium

**Files:**
- Create: `home-assistant-amb/config/blueprints/automation/custom/window_heat_alert.yaml`

**Interfaces:**
- Consumes: comparison sensor state (`warmer|equal|cooler`), numeric indoor/outdoor sensor states, activation helper date, and two sent flags from Task 1.
- Produces: one J16 close notification after a valid/continuous warmer relation and one open notification after a valid/continuous cooler transition. It calls `input_boolean.turn_on` only after notification service action.

- [ ] **Step 1: Create blueprint**

Create `home-assistant-amb/config/blueprints/automation/custom/window_heat_alert.yaml`:

```yaml
blueprint:
  name: Window heat alert
  description: Send one close and one open window alert for an active floor.
  domain: automation
  input:
    floor_name:
      name: Floor name
      selector:
        text: {}
    comparison_sensor:
      name: Comparison sensor
      selector:
        entity:
          domain: sensor
    indoor_temperature_sensor:
      name: Indoor temperature sensor
      selector:
        entity:
          domain: sensor
          device_class: temperature
    outdoor_temperature_sensor:
      name: Outdoor temperature sensor
      selector:
        entity:
          domain: sensor
          device_class: temperature
    activation_date_helper:
      name: Activation date helper
      selector:
        entity:
          domain: input_datetime
    close_sent_helper:
      name: Close sent helper
      selector:
        entity:
          domain: input_boolean
    open_sent_helper:
      name: Open sent helper
      selector:
        entity:
          domain: input_boolean

mode: restart

variables:
  floor_name: !input floor_name
  comparison_sensor: !input comparison_sensor
  indoor_temperature_sensor: !input indoor_temperature_sensor
  outdoor_temperature_sensor: !input outdoor_temperature_sensor
  activation_date_helper: !input activation_date_helper
  close_sent_helper: !input close_sent_helper
  open_sent_helper: !input open_sent_helper

trigger:
  - id: close_crossing
    platform: state
    entity_id: !input comparison_sensor
    to: warmer
    for: "00:05:00"
  - id: close_activation
    platform: state
    entity_id: !input activation_date_helper
  - id: open_crossing
    platform: state
    entity_id: !input comparison_sensor
    to: cooler
    for: "00:05:00"

condition: []

action:
  - choose:
      - conditions:
          - condition: trigger
            id: close_activation
          - condition: template
            value_template: "{{ trigger.to_state.state == now().date() | string }}"
          - condition: state
            entity_id: !input comparison_sensor
            state: warmer
        sequence:
          - delay: "00:05:00"
          - condition: template
            value_template: >-
              {{ states(activation_date_helper) == now().date() | string and
                 states(comparison_sensor) == 'warmer' and
                 is_state(close_sent_helper, 'off') }}
          - service: notify.mobile_app_j16
            data:
              title: "Close windows - {{ floor_name }}"
              message: >-
                Outside has been warmer than the {{ floor_name | lower }} for 5 minutes.
                Outside: {{ states(outdoor_temperature_sensor) | float | round(1) }}°C.
                {{ floor_name }}: {{ states(indoor_temperature_sensor) | float | round(1) }}°C.
              data:
                url: /dashboard-climate/inside-vs-outside
          - service: input_boolean.turn_on
            target:
              entity_id: !input close_sent_helper
      - conditions:
          - condition: trigger
            id: close_crossing
          - condition: template
            value_template: >-
              {{ trigger.from_state is not none and
                 trigger.from_state.state in ['warmer', 'equal', 'cooler'] and
                 states(activation_date_helper) == now().date() | string and
                 is_state(close_sent_helper, 'off') }}
        sequence:
          - service: notify.mobile_app_j16
            data:
              title: "Close windows - {{ floor_name }}"
              message: >-
                Outside has been warmer than the {{ floor_name | lower }} for 5 minutes.
                Outside: {{ states(outdoor_temperature_sensor) | float | round(1) }}°C.
                {{ floor_name }}: {{ states(indoor_temperature_sensor) | float | round(1) }}°C.
              data:
                url: /dashboard-climate/inside-vs-outside
          - service: input_boolean.turn_on
            target:
              entity_id: !input close_sent_helper
      - conditions:
          - condition: trigger
            id: open_crossing
          - condition: template
            value_template: >-
              {{ trigger.from_state is not none and
                 trigger.from_state.state in ['warmer', 'equal'] and
                 states(activation_date_helper) == now().date() | string and
                 is_state(open_sent_helper, 'off') }}
        sequence:
          - service: notify.mobile_app_j16
            data:
              title: "Open windows - {{ floor_name }}"
              message: >-
                Outside has been cooler than the {{ floor_name | lower }} for 5 minutes.
                Outside: {{ states(outdoor_temperature_sensor) | float | round(1) }}°C.
                {{ floor_name }}: {{ states(indoor_temperature_sensor) | float | round(1) }}°C.
              data:
                url: /dashboard-climate/inside-vs-outside
          - service: input_boolean.turn_on
            target:
              entity_id: !input open_sent_helper
```

- [ ] **Step 2: Validate configuration**

Run: `cd home-assistant-amb && just test`

Expected: no output and exit code `0`.

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/blueprints/automation/custom/window_heat_alert.yaml
```

### Task 3: Schedule forecast activation and configure floors
**Complexity:** Medium

**Files:**
- Create: `home-assistant-amb/config/automation/window_heat_alerts.yaml`

**Interfaces:**
- Consumes: Task 1 helpers/sensors, Task 2 blueprint, and `sensor.weather_forecast_hourly` attribute `forecast` entries with `datetime` and `temperature` fields.
- Produces: daily activation notification and three independent blueprint automations for Ground floor, First floor, and Second floor.

- [ ] **Step 1: Add activation automation and blueprint instances**

Create `home-assistant-amb/config/automation/window_heat_alerts.yaml`:

```yaml
- id: window_heat_alert_daily_activation
  alias: Window heat alert daily activation
  trigger:
    - platform: time
      at: "08:00:00"
  variables:
    today: "{{ now().date() | string }}"
    forecast_max: >-
      {% set ns = namespace(maximum=none) %}
      {% for item in state_attr('sensor.weather_forecast_hourly', 'forecast') | default([], true) %}
        {% set timestamp = as_datetime(item.datetime, default=none) %}
        {% set temperature = item.temperature | float(none) %}
        {% if timestamp is not none and temperature is number and timestamp > now() and as_local(timestamp).date() == now().date() %}
          {% if ns.maximum is none or temperature > ns.maximum %}
            {% set ns.maximum = temperature %}
          {% endif %}
        {% endif %}
      {% endfor %}
      {{ ns.maximum }}
  action:
    - service: input_boolean.turn_off
      target:
        entity_id:
          - input_boolean.window_heat_ground_floor_close_sent
          - input_boolean.window_heat_ground_floor_open_sent
          - input_boolean.window_heat_first_floor_close_sent
          - input_boolean.window_heat_first_floor_open_sent
          - input_boolean.window_heat_second_floor_close_sent
          - input_boolean.window_heat_second_floor_open_sent
    - service: input_datetime.set_datetime
      target:
        entity_id: input_datetime.window_heat_alert_activation_date
      data:
        date: "{{ (now().date() - timedelta(days=1)) | string }}"
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ forecast_max | float(none) is not none and forecast_max | float > 25 }}"
          sequence:
            - service: input_datetime.set_datetime
              target:
                entity_id: input_datetime.window_heat_alert_activation_date
              data:
                date: "{{ today }}"
            - service: notify.mobile_app_j16
              data:
                title: Window alerts activated
                message: >-
                  Today's remaining forecast reaches {{ forecast_max | float | round(1) }}°C.
                  Window guidance is active for all floors.
                data:
                  url: /dashboard-climate/inside-vs-outside
  mode: single

- id: window_heat_alert_ground_floor
  alias: Window heat alert - Ground floor
  use_blueprint:
    path: custom/window_heat_alert.yaml
    input:
      floor_name: Ground floor
      comparison_sensor: sensor.window_heat_ground_floor_comparison
      indoor_temperature_sensor: sensor.climate_ground_floor_temperature
      outdoor_temperature_sensor: sensor.openweathermap_temperature
      activation_date_helper: input_datetime.window_heat_alert_activation_date
      close_sent_helper: input_boolean.window_heat_ground_floor_close_sent
      open_sent_helper: input_boolean.window_heat_ground_floor_open_sent

- id: window_heat_alert_first_floor
  alias: Window heat alert - First floor
  use_blueprint:
    path: custom/window_heat_alert.yaml
    input:
      floor_name: First floor
      comparison_sensor: sensor.window_heat_first_floor_comparison
      indoor_temperature_sensor: sensor.climate_first_floor_temperature
      outdoor_temperature_sensor: sensor.openweathermap_temperature
      activation_date_helper: input_datetime.window_heat_alert_activation_date
      close_sent_helper: input_boolean.window_heat_first_floor_close_sent
      open_sent_helper: input_boolean.window_heat_first_floor_open_sent

- id: window_heat_alert_second_floor
  alias: Window heat alert - Second floor
  use_blueprint:
    path: custom/window_heat_alert.yaml
    input:
      floor_name: Second floor
      comparison_sensor: sensor.window_heat_second_floor_comparison
      indoor_temperature_sensor: sensor.climate_second_floor_temperature
      outdoor_temperature_sensor: sensor.openweathermap_temperature
      activation_date_helper: input_datetime.window_heat_alert_activation_date
      close_sent_helper: input_boolean.window_heat_second_floor_close_sent
      open_sent_helper: input_boolean.window_heat_second_floor_open_sent
```

- [ ] **Step 2: Validate configuration**

Run: `cd home-assistant-amb && just test`

Expected: no output and exit code `0`.

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/automation/window_heat_alerts.yaml
```

### Task 4: Run repository checks and verify live behavior
**Complexity:** Low

**Files:** None

**Interfaces:**
- Consumes: completed Tasks 1-3.
- Produces: validated YAML and live confirmation that all fourteen source-spec manual cases behave correctly.

- [ ] **Step 1: Run final validation**

```bash
cd home-assistant-amb && just test
cd .. && pre-commit run --all-files
```

Expected: `just test` has no output and exit code `0`; all pre-commit hooks pass.

- [ ] **Step 2: Deploy YAML-only configuration**

On Raspberry Pi in `home-assistant-amb`:

```bash
git pull
```

Reload Template Entities, Automations, and Helpers in Developer Tools -> YAML, or restart Home Assistant. Do not run Docker rebuild: image is unchanged.

- [ ] **Step 3: Verify manual behavior matrix**

In Developer Tools, use temporary sensor states / automation traces and confirm:

1. Forecast maximum `25` produces no activation; `25.1` produces one notification and today activation date.
2. Missing, empty, malformed, past-only, or nonnumeric forecast data produces no activation or notification.
3. Each comparison sensor is unavailable for unavailable/nonnumeric source values; valid pairs yield correct `warmer`, `equal`, or `cooler` state.
4. A warmer transition under five minutes sends nothing; five uninterrupted minutes sends one close notification for correct floor.
5. A cooler transition under five minutes sends nothing; five uninterrupted minutes sends one open notification for correct floor, even with close flag off.
6. Initial warmer activation sends close only after five minutes; initial cooler activation sends no open notification.
7. Repeated same-direction transitions do not send twice after relevant flag is on; three simultaneous floor crossings deliver three separate notifications.
8. Restart after a sent notification retains activation/flag state and does not duplicate; restart during timer requires fresh five minutes.
9. On next 08:00, all six flags reset whether forecast qualifies or not; next qualifying day can send all alerts again.

- [ ] **Step 4: Commit formatting corrections only if hooks changed files**

```bash
git status --short
```

Expected: commit only if `pre-commit` modified files. Otherwise make no extra commit.
