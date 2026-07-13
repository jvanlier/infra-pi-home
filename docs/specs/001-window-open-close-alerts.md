# Spec 001 — Per-Floor Window Open/Close Alerts

Opus 4.8

## Summary

On hot days, notify me (per floor) when to **close** windows because it has
become warmer outside than inside that floor, and later when to **open** them
again because it has cooled back below inside. Each alert fires **at most once
per direction per floor per day**. A morning confirmation tells me the system is
armed for the day.

There are three floors, each with its own average inside temperature, so on a
given hot day I can receive up to **3 close alerts** and **3 open alerts**,
staggered independently by floor.

## Motivation

The Climate dashboard already has an "Inside versus outside temperature" chart
(`home-assistant-amb/config/dashboard/climate.yaml`) plotting the three floor
averages against the outside temperature. The pattern this system automates is:
when it is hotter outside than in, keep windows shut to hold the cool; when it
drops below the indoor temperature, open up to let the heat out. Doing this by
eye off the chart is easy to forget. This system pushes the decision points.

## Goals

- Alert to **close** windows for a floor when outside temp rises above that
  floor's inside temp, on qualifying hot days.
- Alert to **open** windows for a floor when outside temp drops back below that
  floor's inside temp.
- Fire each alert **once per direction per floor per day** (no flip-flopping
  when temperatures hover near equal).
- Only operate on days forecast to exceed the threshold (default 25 °C).
- Send a morning confirmation that the system is armed for the day.
- Handle the case where it is already hotter outside than inside at arm time.

## Non-Goals

- No physical window actuation — advisory notifications only.
- No per-room granularity — floor averages only (matching the existing
  `sensor.climate_{ground,first,second}_floor_temperature` sensors).
- No humidity/CO₂/air-quality consideration — temperature only.
- The attic remains excluded (it is excluded from the second-floor average by
  design; see project `CLAUDE.md`).

## Decisions (from clarifying dialogue)

| Topic | Decision |
|---|---|
| Hot-day gate | **Forecast max ≥ threshold** at morning check, using `sensor.weather_forecast_hourly`. Forecast-only (no live fallback). |
| Morning check time | **08:00** fixed, daily. |
| Confirmation | Push on hot days only ("system armed"). No message on non-hot days. |
| Crossing logic | **Exact crossing** (outside > inside) via template binary sensor edges + **once-per-direction-per-day latch** booleans. No hysteresis margin. |
| Open gating | Open fires **independently** of close (naturally cannot false-fire because a downward edge requires a prior upward one, and the open branch requires the system to be armed). |
| Already hot at 08:00 | **Send close alert immediately** for any floor already "warmer outside" at arm time. |
| Threshold | **`input_number` helper** (`window_alert_temp_threshold`, default 25 °C), UI-tunable. |
| Notify target | **`notify.mobile_app_j16`** (single phone, for testing without disturbing others) with **deep-link** to the climate chart. |
| Structure | **Blueprint + 3 instances** (matches `heating_needed_alert` / `water_leak`). |

## Architecture

### Entities & helpers

**Template binary sensors** — new file `config/template/window_alerts.yaml`
(the `template/` dir is already `!include_dir_merge_list`-merged):

- `binary_sensor.outside_warmer_than_ground_floor`
- `binary_sensor.outside_warmer_than_first_floor`
- `binary_sensor.outside_warmer_than_second_floor`

Each: `state = outside_temp > floor_inside_temp`, with an `availability` guard
mirroring `climate_floor_averages.yaml` — unavailable when either input is not a
number, so a dead sensor produces no spurious edges.

- Outside: `sensor.openweathermap_temperature`
- Inside: `sensor.climate_{ground,first,second}_floor_temperature`

**Input booleans** — added to `config/input_boolean.yaml`:

- `window_alert_active` — armed-for-today flag, set by the morning check.
- `window_close_alerted_ground`, `window_close_alerted_first`,
  `window_close_alerted_second` — per-floor close latches.
- `window_open_alerted_ground`, `window_open_alerted_first`,
  `window_open_alerted_second` — per-floor open latches.

(7 booleans total. Per-floor latches guarantee once-per-direction-per-day even
across HA restarts.)

**Input number** — added to `config/input_number.yaml`:

- `window_alert_temp_threshold` — hot-day gate, default `25`, range ~20–35,
  step 0.5. Matches existing threshold helpers
  (`fridge_temperature_threshold`, `illuminance_threshold_*`).

### Automations

**1. Morning arm** — new file `config/automation/window_alerts_arm.yaml`
(single automation, not a blueprint):

- **Trigger:** `platform: time`, `at: "08:00:00"`.
- **Compute today's forecast max** from the `forecast` attribute of
  `sensor.weather_forecast_hourly` (list of hourly entries with `datetime` +
  `temperature`, same structure the climate chart's `data_generator` consumes).
  Filter entries to today (`as_local(as_datetime(e.datetime)).date() == now().date()`),
  take the max temperature.
- **Action (`choose`):**
  - **If** `max >= states('input_number.window_alert_temp_threshold')`:
    turn **on** `window_alert_active`; turn **off** all 6 latch booleans;
    push confirmation
    _"🪟 Window alerts armed — hot day ahead (max ~{{max}}°). I'll tell you when
    to open/close windows per floor."_ with deep-link.
  - **Else:** turn **off** `window_alert_active` (idempotent disarm); no push.
- If the forecast is empty/unavailable → treated as **not hot** → disarm, no
  push. (Known limitation — see below.)

Turning `window_alert_active` **on** is also the trigger that lets the blueprint
instances handle the "already hot at 08:00" case (see below).

**2. Window-alert blueprint** — new file
`config/blueprints/automation/custom/window_alert.yaml`, instantiated 3× in
`config/automation/window_alerts.yaml`.

**Blueprint inputs:**

- `outside_warmer_sensor` — the floor's `binary_sensor.outside_warmer_than_*`
- `floor_name` — display string, e.g. `"ground-floor"`
- `inside_sensor` — `sensor.climate_*_floor_temperature` (for message text)
- `outside_sensor` — `sensor.openweathermap_temperature` (for message text)
- `close_latch` — the floor's `input_boolean.window_close_alerted_*`
- `open_latch` — the floor's `input_boolean.window_open_alerted_*`

**Triggers (two):**

1. `outside_warmer_sensor` changes state (the normal midday/evening edges).
2. `input_boolean.window_alert_active` turns **on** (the 08:00 arm moment).

**Action (`choose`), guarded on `window_alert_active == 'on'`:**

- **Close branch** — `outside_warmer_sensor == 'on'` **and** `close_latch == 'off'`:
  push _"🌡️ Close {{floor_name}} windows — it's now warmer outside
  ({{outside}}°) than inside ({{inside}}°)."_; set `close_latch` on.
- **Open branch** — `outside_warmer_sensor == 'off'` **and** `open_latch == 'off'`:
  push _"🪟 Open {{floor_name}} windows — it's cooler outside ({{outside}}°)
  than inside ({{inside}}°) now."_; set `open_latch` on.

`mode: restart`.

**Three instances** in `config/automation/window_alerts.yaml`, one per floor,
wiring the floor-specific sensors and latch booleans.

### Notifications

- Service: `notify.mobile_app_j16`.
- `data.url: /dashboard-climate/inside-vs-outside` (deep-links to the
  "Inside vs Outside" climate view — confirmed from `lovelace.yaml` dashboard id
  `dashboard-climate` + view `path: inside-vs-outside`).

## Data Flow (hot day, ground floor example)

1. **08:00** — arm automation reads forecast max, say 29 °.
2. `29 ≥ 25` → `window_alert_active` on; all 6 latches reset off; confirmation
   push sent.
3. **Late morning** — outside climbs past ground-floor inside;
   `binary_sensor.outside_warmer_than_ground_floor` flips off→on.
4. Ground-floor blueprint instance triggers on the edge → close branch
   (armed, latch off) → **close** push; `window_close_alerted_ground` on.
5. Later wiggles across the line re-trigger the edge but the close latch is on →
   suppressed. ✅ One close alert.
6. **Evening** — outside drops back below ground-floor inside; binary sensor
   flips on→off.
7. Blueprint triggers → open branch (armed, open latch off) → **open** push;
   `window_open_alerted_ground` on.
8. Floors run independently → up to 3 close + 3 open alerts, staggered.
9. **Next 08:00** — latches reset; if forecast < threshold, stays disarmed
   (no confirmation, no alerts).

## Edge Cases

- **Forecast unavailable at 08:00** → treated as not-hot → disarm, no push.
  *Known limitation:* a hot day would be missed if the forecast sensor is down
  at exactly 08:00. Acceptable per the forecast-only decision.
- **Sensor unavailable** → binary sensor `availability` guard makes it
  unavailable → no spurious edges, no alerts for that floor.
- **Already hotter outside than a floor's inside at 08:00** → binary sensor is
  already `on`, so no off→on edge fires; instead the blueprint's trigger #2
  (`window_alert_active` → on) fires, the close branch sees warmer-outside
  already true and the latch off → **immediate close alert**. No duplicated
  notify logic in the arm automation.
- **On→off edge before 08:00 arming** → open branch requires
  `window_alert_active == 'on'`, so it is suppressed until armed.
- **HA restart mid-day** → latch booleans persist state, so already-sent alerts
  are not repeated.

## Files Created / Changed

| File | Change |
|---|---|
| `config/template/window_alerts.yaml` | **New** — 3 `outside_warmer_than_*` binary sensors |
| `config/blueprints/automation/custom/window_alert.yaml` | **New** — window-alert blueprint |
| `config/automation/window_alerts.yaml` | **New** — 3 blueprint instances (one per floor) |
| `config/automation/window_alerts_arm.yaml` | **New** — 08:00 forecast-gate arm automation |
| `config/input_boolean.yaml` | **Edit** — +7 booleans (1 active + 6 latches) |
| `config/input_number.yaml` | **Edit** — +1 `window_alert_temp_threshold` |

All paths relative to `home-assistant-amb/`.

## Testing & Validation

This repo validates config via `hass --script check_config` only (no automation
*logic* test harness), so:

1. **Config validation:** `just test` must pass (validates new template
   sensors, blueprint, automations, helpers). Run immediately before commit
   (per project `CLAUDE.md`); commit/push only if it passes.
2. **Template sanity:** dry-run the forecast-max Jinja in Developer Tools →
   Template against live `sensor.weather_forecast_hourly` before relying on it.
3. **Live verification** on the Pi (checkout branch + reload config; image
   unchanged, so no rebuild):
   - **Arm path:** lower `window_alert_temp_threshold` below current forecast
     max, run the arm automation → confirm "armed" push.
   - **Close alert:** while armed, drive a floor's `outside_warmer_than_*` to
     `on` → confirm one close push + latch set; re-toggle → confirm no repeat.
   - **Open alert:** flip the binary sensor back → confirm open push.
   - **Already-hot-at-08:00:** with a floor already warmer-outside, run the arm
     automation → confirm immediate close alert for that floor.
   - **Non-hot day:** threshold above forecast max → arm runs → no push,
     `window_alert_active` off, no floor alerts fire.

## Deployment

Config-only change (no `Dockerfile`/image change). Per project `CLAUDE.md`:
create a branch, run `just test`, commit, push (CI re-validates), then on the
Pi checkout the branch and reload configuration / restart via UI. New helpers
in `input_boolean.yaml` / `input_number.yaml` require a restart or the relevant
reload to register.

## Open Questions / Future Enhancements

- Optional hysteresis margin + debounce if exact-crossing latching proves too
  twitchy in practice (currently deferred — YAGNI).
- Optional switch from `notify.mobile_app_j16` to `notify.notify` once tested,
  to alert the whole household.
- Optional consideration of humidity when deciding to open (deferred).
