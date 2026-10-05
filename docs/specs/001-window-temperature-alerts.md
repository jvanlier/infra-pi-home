# Window Temperature Alerts per Floor

## Status

Approved design specification.

## Summary

System activates at 08:00 only when highest remaining hourly OpenWeatherMap forecast temperature for current local day is strictly above 25°C. Open guidance requires a five-minute cooling condition and is sent only after that floor's close alert. For each floor, current outside temperature and the remaining forecast maximum must both be at least 0.5°C below the floor temperature.

On active days, J16 receives one activation confirmation plus at most one close and one open alert per floor. An open alert is never sent before the corresponding close alert.

## Goals

- Activate window guidance only on qualifying hot days.
- Confirm activation once at 08:00.
- Detect close crossover and forecast-safe open readiness independently per floor.
- Send separate close and guarded open notifications for each floor.
- Require every alert condition to remain stable for five minutes.
- Prevent duplicate same-day notifications despite temperature fluctuations.
- Preserve activation and one-shot state across Home Assistant restarts.
- Reuse per-floor logic through custom automation blueprint.

## Non-goals

- Detect actual window state.
- Automatically open or close windows.
- Retry activation after 08:00.
- Send inactive-status notifications on cool days.
- Add dashboard controls or user-configurable thresholds/times.
- Change chart, floor-average sensors, or floor room membership.
- Include attic in second-floor average.

## Existing entities

Outdoor source:

- `sensor.openweathermap_temperature`
- `sensor.weather_forecast_hourly`, using `forecast` attribute

Indoor sources:

- `sensor.climate_ground_floor_temperature`
- `sensor.climate_first_floor_temperature`
- `sensor.climate_second_floor_temperature`

Notification target:

- `notify.mobile_app_j16`

Notification link:

- `/dashboard-climate/inside-vs-outside`

## Proposed components

### Per-floor comparison template sensors

Add `home-assistant-amb/config/template/window_heat_alerts.yaml` with one sensor per floor. Each sensor compares current outdoor temperature with corresponding floor average and has one of these states:

- `warmer` when outside temperature is strictly greater than floor temperature
- `equal` when temperatures are equal
- `cooler` when outside temperature is strictly less than floor temperature

Sensors must be unavailable unless both source states are numeric. They must not substitute zero or another default for missing temperature data.

Suggested entity IDs:

- `sensor.window_heat_ground_floor_comparison`
- `sensor.window_heat_first_floor_comparison`
- `sensor.window_heat_second_floor_comparison`

### Remaining forecast maximum and open-readiness sensors

`sensor.window_heat_forecast_max_today` continues to select the maximum numeric future-today forecast temperature for daily activation. Its boolean `remaining_forecast_complete` attribute is false when `forecast` is missing or not a list, any row has a missing or unparseable `datetime`, or any valid future-today row has a missing or nonnumeric `temperature`; otherwise it is true.

Add these binary sensors. Each is unavailable unless its floor temperature, outdoor temperature, and remaining forecast maximum are numeric and `remaining_forecast_complete` is true:

- `binary_sensor.window_heat_ground_floor_safe_to_open`
- `binary_sensor.window_heat_first_floor_safe_to_open`
- `binary_sensor.window_heat_second_floor_safe_to_open`

Each readiness sensor is on exactly when both `current outdoor temperature <= current floor temperature - 0.5°C` and `remaining forecast maximum <= current floor temperature - 0.5°C`.

### Persistent helpers

Add one date-only helper to `home-assistant-amb/config/input_datetime.yaml`:

- `input_datetime.window_heat_alert_activation_date`

System is active exactly when helper date equals current Home Assistant local date.

Add six helpers to `home-assistant-amb/config/input_boolean.yaml`:

- `input_boolean.window_heat_ground_floor_close_sent`
- `input_boolean.window_heat_ground_floor_open_sent`
- `input_boolean.window_heat_first_floor_close_sent`
- `input_boolean.window_heat_first_floor_open_sent`
- `input_boolean.window_heat_second_floor_close_sent`
- `input_boolean.window_heat_second_floor_open_sent`

Do not give sent flags an `initial` value. Home Assistant must restore them after restart.

### Reusable floor blueprint

Add `home-assistant-amb/config/blueprints/automation/custom/window_heat_alert.yaml`.

Blueprint inputs:

- Human-readable floor name
- Comparison sensor for close alerts
- Open-readiness binary sensor (`open_readiness_sensor`)
- Outdoor temperature sensor
- Forecast maximum sensor for close-alert forecast guard
- Activation-date helper
- Close-sent helper
- Open-sent helper

Blueprint owns all per-floor crossover, readiness, five-minute confirmation, notification, and one-shot behavior. Notification target can remain fixed to J16 because this feature has one selected destination.

### Automation configuration

Add `home-assistant-amb/config/automation/window_heat_alerts.yaml` containing:

1. One daily activation automation.
2. Three concise blueprint instances, one for each floor.

Only floor names and entity mappings should differ between blueprint instances.

## Functional behavior

### Daily activation

At exactly 08:00 local time:

1. Reset all six sent flags.
2. Ensure activation date does not indicate current day before forecast evaluation.
3. Read `forecast` from `sensor.weather_forecast_hourly`.
4. Keep forecast entries whose timestamps:
   - are in future relative to evaluation time, and
   - resolve to current Home Assistant local date.
5. Find maximum valid temperature among remaining entries.
6. Activate only when maximum is strictly greater than 25°C.

When qualifying:

- Set activation date to current local date.
- Send exactly one J16 notification.
- Include forecast maximum and explain that per-floor window alerts are active.
- Link notification to existing Inside versus Outside chart.

When not qualifying, when no current-day future entries exist, or when forecast data is unavailable/malformed:

- Keep system inactive.
- Send no notification.
- Do not retry later that day.

If Home Assistant is offline at 08:00, activation is missed for that day. Startup must not perform delayed activation.

### Close alert

For each floor independently:

- Trigger when comparison enters `warmer` from a valid prior comparison state and remains `warmer` continuously for five minutes.
- Require activation date to equal current local date.
- Require floor close-sent helper to be off.
- Send one separate J16 close notification for that floor.
- Include floor name plus current outside and floor temperatures.
- Link to existing chart.
- Turn on floor close-sent helper after notification action.

If system activates while floor comparison is already `warmer`, blueprint must treat activation as a candidate close condition. It waits five minutes, verifies condition remained warmer, then sends close alert if not already sent.

### Open alert

- Trigger only when the floor's open-readiness sensor transitions `off -> on` and remains on continuously for five minutes.
- Each floor's open readiness requires current outside temperature and the remaining forecast maximum to both be at least 0.5°C below its indoor temperature.
- Require activation date to equal current local date.
- Require floor close-sent helper to be on.
- Require floor open-sent helper to be off.
- Require the readiness state to have changed no earlier than daily activation.
- Send one separate J16 open notification for that floor.
- Include the cooling margin, current outside temperature, floor name, and confirmation that the remaining forecast stays at least 0.5°C below indoor temperature.
- Link to existing chart.
- Turn on floor open-sent helper after notification action.

Open alert must never be sent before the corresponding close notification. If the close alert is suppressed or never sent, the open alert is also suppressed.

Initial on state at activation, restart/reload state restoration, and `unknown`/`unavailable -> on` recovery must not produce an open alert. Only a subsequent qualifying `off -> on` transition may start the five-minute timer.

### Duplicate prevention

- Each sent flag is independent.
- Once a floor close flag is on, later warmer crossings that day do not notify.
- Once a floor open flag is on, later qualifying readiness transitions that day do not notify.
- Flags reset at next 08:00 evaluation, whether next day qualifies or not.
- Three floor automations must run independently so simultaneous crossovers cannot suppress another floor's alert.

Maximum notifications on one qualifying day:

- One activation confirmation
- Three close notifications
- Three open notifications

## Notification copy

Exact wording may be adjusted during implementation, but intent must remain clear.

Activation example:

- Title: `Window alerts activated`
- Message: `Today's remaining forecast reaches 27.3°C. Window guidance is active for all floors.`

Close example:

- Title: `Close windows - First floor`
- Message: `Outside has been warmer than the first floor for 5 minutes. Outside: 24.8°C. First floor: 24.5°C.`

Open example:

- Title: `Open windows - First floor`
- Message: `It is at least 0.5°C cooler outside (23.7°C) than on the first floor. Today's remaining forecast also stays at least 0.5°C below the indoor temperature.`

## State and restart behavior

- Activation date and sent flags restore across restart.
- Restart must not clear already-sent state or cause duplicate same-day notifications.
- Five-minute `for` timers do not need durable elapsed-time persistence. After restart/reload, implementation may require a fresh stable period or next valid transition, but must never send immediately from stale, unknown, or unavailable data.
- Existing warmer condition may be safely reconciled for unsent close guidance because closing is actionable whenever active day resumes. Open readiness must not be interpreted as an open transition unless its prior state was off.

## Error handling

- Forecast parsing must tolerate missing attribute, empty list, invalid timestamps, and nonnumeric temperatures.
- A wholly or partially malformed forecast sets `remaining_forecast_complete` false. Open readiness is unavailable and cannot notify, even if a numeric maximum can still be derived from other rows.
- Temperature comparisons and open readiness must expose unavailable state when their required source states are unavailable or nonnumeric.
- Do not activate or notify from partial/defaulted values.
- Notification service failure must be visible through Home Assistant automation trace/log. No retry subsystem is required.

## Validation

Required repository validation:

```bash
cd home-assistant-amb
just test
```

Also run:

```bash
pre-commit run --all-files
```

Manual behavior matrix:

1. Remaining forecast maximum exactly 25°C: inactive, no notification.
2. Remaining forecast maximum above 25°C: active, one confirmation.
3. Forecast unavailable or empty at 08:00: inactive, no notification.
4. Warmer state under five minutes: no close alert.
5. Warmer state for five minutes: correct floor close alert.
6. Repeated warmer crossings: no second close alert that day.
7. After a close alert, a five-minute shallow dip that is less than 0.5°C cooler: no open alert. A forecasted rebound above current outside temperature is allowed only if its forecast remains at least 0.5°C below that floor's indoor temperature.
8. Full open-readiness invariant held continuously for five minutes after `off -> on`, with close-sent on: exactly one correct-floor open alert.
9. Missing forecast or mixed valid/malformed forecast: readiness unavailable and no open alert.
10. Open readiness recovery from `unknown` or `unavailable` directly to on: no open alert.
11. Open readiness with close-sent off: no open alert.
12. Three near-simultaneous floor conditions: three separate notifications, each only after its floor's close alert.
13. Source temperature unavailable: no comparison or readiness alert.
14. Restart after sent alert: no duplicate.
15. Next qualifying day: flags reset and all alerts can occur again.

## Acceptance criteria

- At 08:00, system activates only if highest remaining hourly forecast for current local day is greater than 25°C.
- J16 receives one activation confirmation only on qualifying days.
- Each floor independently sends no more than one close and one open alert per active day.
- Every close crossover and open-readiness alert requires five continuous minutes in its target relation.
- An open alert requires the corresponding close-sent helper to be on, `remaining_forecast_complete == true`, and an `off -> on` readiness transition after activation. For each floor, current outside temperature and remaining forecast maximum must both be at least 0.5°C below indoors.
- A missing, malformed, or partially malformed forecast and any nonnumeric/unavailable required input cannot produce an open alert.
- Temperature fluctuations cannot create duplicate same-day alerts.
- Open alerts are sent only after the corresponding close notification.
- Ground, first, and second floor alerts use existing floor-average entities.
- Existing chart and floor averaging remain unchanged.
- Home Assistant configuration validation and pre-commit checks pass.
