# Window Temperature Alerts per Floor

## Status

Approved design specification.

## Summary

Add a Home Assistant notification system that recommends closing or opening windows independently for ground, first, and second floors on forecast hot days. System activates at 08:00 only when highest remaining hourly OpenWeatherMap forecast temperature for current local day is strictly above 25°C.

On active days, J16 receives one activation confirmation plus at most one close and one open alert per floor. Alerts use existing outside temperature and floor-average temperature entities shown in Inside versus Outside chart.

## Goals

- Activate window guidance only on qualifying hot days.
- Confirm activation once at 08:00.
- Detect inside/outside temperature crossover independently per floor.
- Send separate close and open notifications for each floor.
- Require crossover condition to remain stable for five minutes.
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
- Comparison sensor
- Indoor floor temperature sensor
- Outdoor temperature sensor
- Activation-date helper
- Close-sent helper
- Open-sent helper

Blueprint owns all per-floor crossover, five-minute confirmation, notification, and one-shot behavior. Notification target can remain fixed to J16 because this feature has one selected destination.

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

For each floor independently:

- Trigger when comparison enters `cooler` from a valid prior comparison state and remains `cooler` continuously for five minutes.
- Require activation date to equal current local date.
- Require floor open-sent helper to be off.
- Send one separate J16 open notification for that floor.
- Include floor name plus current outside and floor temperatures.
- Link to existing chart.
- Turn on floor open-sent helper after notification action.

Open alert must not require close-sent helper to be on. A valid cooler crossover may alert even when no close notification was sent earlier.

Initial `cooler` state at activation must not produce morning open alert. Open requires a subsequent valid transition into cooler state.

### Duplicate prevention

- Each sent flag is independent.
- Once a floor close flag is on, later warmer crossings that day do not notify.
- Once a floor open flag is on, later cooler crossings that day do not notify.
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
- Message: `Outside has been cooler than the first floor for 5 minutes. Outside: 23.7°C. First floor: 24.1°C.`

## State and restart behavior

- Activation date and sent flags restore across restart.
- Restart must not clear already-sent state or cause duplicate same-day notifications.
- Invalid startup transitions from `unknown` or `unavailable` must not count as open crossover.
- Five-minute `for` timers do not need durable elapsed-time persistence. After restart/reload, implementation may require a fresh stable period or next valid transition, but must never send immediately from stale/unknown data.
- Existing warmer condition may be safely reconciled for unsent close guidance because closing is actionable whenever active day resumes. Existing cooler condition must not be interpreted as open crossover without valid transition context.

## Error handling

- Forecast parsing must tolerate missing attribute, empty list, invalid timestamps, and nonnumeric temperatures.
- Temperature comparisons must expose unavailable state when either source is unavailable or nonnumeric.
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
7. Cooler state under five minutes: no open alert.
8. Cooler state for five minutes: correct floor open alert.
9. Open crossover with close-sent off: open alert still occurs.
10. Initial cooler state at activation: no open alert.
11. Three near-simultaneous floor crossovers: three separate notifications.
12. Source temperature unavailable: no comparison alert.
13. Restart after sent alert: no duplicate.
14. Next qualifying day: flags reset and all alerts can occur again.

## Acceptance criteria

- At 08:00, system activates only if highest remaining hourly forecast for current local day is greater than 25°C.
- J16 receives one activation confirmation only on qualifying days.
- Each floor independently sends no more than one close and one open alert per active day.
- Every crossover alert requires five continuous minutes in target relation.
- Temperature fluctuations cannot create duplicate same-day alerts.
- Open alerts do not depend on close notification state.
- Ground, first, and second floor alerts use existing floor-average entities.
- Missing or invalid source data cannot produce false alerts.
- Existing chart and floor averaging remain unchanged.
- Home Assistant configuration validation and pre-commit checks pass.
