# Tesla Home Charging Energy Implementation Plan

**Goal:** Make Tesla home-charging consumption appear as its own branch in Home Assistant's built-in Energy dashboard "Energy flow" Sankey chart, counting only energy charged at home (not on the road/Supercharging).

**Architecture:** TeslaMate already publishes live vehicle telemetry to the shared MQTT broker (`teslamate/cars/1/...`), and this repo already has one working MQTT-sourced sensor (`sensor.tesla_battery_level`, in `home-assistant-amb/config/mqtt.yaml`). This plan adds two more raw MQTT sensors (`charger_power`, `geofence`), a template sensor that zeroes out charger power unless the car's geofence is "Home", and a built-in Riemann-sum (`integration` platform) sensor that turns that gated power into a continuously-growing kWh total suitable for the Energy dashboard. It also adds a new "Tesla" view to the Power dashboard (mirroring the existing Grid/Plugs/Appliances views) and a matching teaser on the Overview dashboard. The very last step — registering the new kWh entity as an "Individual Device" on the Energy dashboard — is a one-time manual UI action (Home Assistant stores that config in `.storage/energy`, not in this repo's YAML), documented as an explicit manual task.

**Tech Stack:** Home Assistant (`ghcr.io/home-assistant/home-assistant:2026.7.0`), YAML configuration, Mosquitto MQTT broker (already running, already connected), TeslaMate (already running, car id `1`, already connected to the broker — no TeslaMate-side changes needed), Home Assistant's built-in `integration` (Riemann sum) sensor platform, `just` task runner, Docker.

## Global Constraints

- Repo root: `/Users/jori.vanlier/dev/private/infra-pi-home-2` (adjust if the builder's checkout path differs; all paths below are relative to repo root).
- All Home Assistant config lives under `home-assistant-amb/config/`.
- Car id in TeslaMate's MQTT topics is `1` (already used by the existing `sensor.tesla_battery_level`).
- The home geofence is named exactly `Home` in TeslaMate (user confirmed, plain text, no emoji, case-sensitive — must match exactly).
- Only home charging counts. Charging while the car's geofence is anything other than `Home` (including empty/no geofence, e.g. Supercharging) must be excluded from the energy total.
- Approach: integrate (Riemann sum) `charger_power` (kW, wall/grid draw), gated to zero outside the `Home` geofence — NOT an automation-driven accumulation of `charge_energy_added` session totals (user confirmed this trade-off: continuous updates, matches how the wall/grid meter sees it, no extra automation/helper state).
- Entity naming ladder (exact, case-sensitive, matches this repo's existing `tesla_battery_level` convention):
  - `sensor.tesla_charger_power` (raw MQTT, kW)
  - `sensor.tesla_geofence` (raw MQTT, text)
  - `sensor.tesla_charger_power_at_home` (template, kW, gated)
  - `sensor.tesla_energy_charged_at_home` (Riemann sum, kWh) — this is the entity registered on the Energy dashboard.
- No `home-assistant-amb/config/configuration.yaml` changes are needed anywhere in this plan — `mqtt: !include mqtt.yaml`, `sensor: !include_dir_merge_list sensor/`, and `template: !include_dir_merge_list template/` are already wired in from prior work.
- Dashboard scope: add a new "Tesla" view (tab) to the Power dashboard (`home-assistant-amb/config/dashboard/power.yaml`), placed after the existing Appliances view, plus a matching "Tesla" subheader + teaser tile on the Overview dashboard's Power section (`home-assistant-amb/config/dashboard/overview.yaml`), placed after the existing Appliances subheader — per this repo's documented convention that sub-dashboard view order must match Overview subheader order (see `CLAUDE.md` "Dashboard Conventions").
- Validate every change with `just build && just test` run from `home-assistant-amb/` before every commit. If `just test` has no output and exits 0, it passed. Never commit if it fails.
- This is a config-only change (no `Dockerfile` or image tag edits) — no `docker compose up -d --build` needed on deploy, only a HA config reload/restart.
- Base branch is `main`. Work happens on one new branch for the whole plan, pushed at the end for CI to validate again.
- Do NOT add anything beyond what's specified here (no extra TeslaMate sensors, no automations, no helpers/counters, no new dashboards beyond the one new view) — YAGNI.

---

### Task 1: Add raw TeslaMate charger power + geofence MQTT sensors

**Estimated Task Complexity:** low

**Files:**
- Modify: `home-assistant-amb/config/mqtt.yaml`

**Interfaces:**
- Produces: `sensor.tesla_charger_power` (`unique_id: tesla_charger_power`, unit `kW`, `device_class: power`, `state_class: measurement`) and `sensor.tesla_geofence` (`unique_id: tesla_geofence`, plain text state, no unit/device class). Task 2 consumes both exact `entity_id`s.

- [ ] **Step 1: Create a feature branch**

Run:
```bash
git checkout main
git pull
git checkout -b feat/tesla-home-charging-energy
```
Expected: branch created and checked out, working tree clean.

- [ ] **Step 2: Add the two new sensors to `home-assistant-amb/config/mqtt.yaml`**

Current full file content:

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

Change to (append two new list entries under the same `sensor:` key):

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

  - name: "Tesla Charger Power"
    unique_id: tesla_charger_power
    state_topic: "teslamate/cars/1/charger_power"
    unit_of_measurement: "kW"
    device_class: power
    state_class: measurement
    availability_topic: "teslamate/cars/1/healthy"
    payload_available: "true"
    payload_not_available: "false"

  - name: "Tesla Geofence"
    unique_id: tesla_geofence
    state_topic: "teslamate/cars/1/geofence"
    availability_topic: "teslamate/cars/1/healthy"
    payload_available: "true"
    payload_not_available: "false"
```

Notes for the implementer:
- `teslamate/cars/1/charger_power` publishes a plain numeric payload in kW (e.g. `7.4`, `0`), no JSON, no `value_template` needed — same shape as the existing `battery_level` topic.
- `teslamate/cars/1/geofence` publishes the plain name of the currently-matched geofence (e.g. `Home`), or an empty payload when the car isn't inside any defined geofence (e.g. driving, Supercharging away from home). No unit/device_class applies to a text sensor like this.
- Both reuse the same `availability_topic`/payloads as the existing battery sensor, so they go `unavailable` together if TeslaMate's logger for the car is unhealthy.

- [ ] **Step 3: Validate**

Run from `home-assistant-amb/`:
```bash
just build && just test
```
Expected: no error output, command exits `0`.

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/mqtt.yaml
git commit -m "feat(ha): add TeslaMate charger power and geofence MQTT sensors"
```

---

### Task 2: Add the home-gating template sensor

**Estimated Task Complexity:** medium

**Files:**
- Create: `home-assistant-amb/config/template/tesla.yaml`

**Interfaces:**
- Consumes: `sensor.tesla_charger_power`, `sensor.tesla_geofence` (Task 1).
- Produces: `sensor.tesla_charger_power_at_home` (`unique_id: tesla_charger_power_at_home`, unit `kW`, `device_class: power`, `state_class: measurement`). Task 3 consumes this exact `entity_id`.

- [ ] **Step 1: Create `home-assistant-amb/config/template/tesla.yaml`**

This file is automatically picked up by the existing `template: !include_dir_merge_list template/` include in `configuration.yaml` — no other file needs editing for this task.

```yaml
- sensor:
  - name: Tesla Charger Power At Home
    unique_id: tesla_charger_power_at_home
    unit_of_measurement: kW
    device_class: power
    state_class: measurement
    state: >-
      {{ states('sensor.tesla_charger_power') | float(0)
         if states('sensor.tesla_geofence') == 'Home' else 0 }}
```

Notes for the implementer:
- This mirrors the existing style in `home-assistant-amb/config/template/power.yaml` (a top-level list with one `sensor:` key holding a list of sensor definitions, `state:` as a single Jinja expression using the `>-` block scalar).
- The Jinja is a ternary: outputs the current charger power only when `sensor.tesla_geofence`'s state is exactly the string `Home`; otherwise outputs `0`. `| float(0)` guards against `sensor.tesla_charger_power` being `unavailable`/`unknown` (e.g. car asleep), defaulting to `0` instead of erroring.
- Do not reference `charging_state` or `plugged_in` — gating on geofence alone is sufficient, since charger power is already `0` whenever the car isn't actually charging.

- [ ] **Step 2: Validate**

Run from `home-assistant-amb/`:
```bash
just build && just test
```
Expected: no error output, command exits `0`.

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/template/tesla.yaml
git commit -m "feat(ha): add Tesla charger power at home gating sensor"
```

---

### Task 3: Add the Riemann-sum home charging energy sensor

**Estimated Task Complexity:** medium

**Files:**
- Create: `home-assistant-amb/config/sensor/tesla_energy.yaml`

**Interfaces:**
- Consumes: `sensor.tesla_charger_power_at_home` (Task 2).
- Produces: `sensor.tesla_energy_charged_at_home` (`unique_id: tesla_energy_charged_at_home`, unit `kWh`, auto-derived `device_class: energy`). Task 4's dashboard tiles and Task 5's Energy-dashboard registration both consume this exact `entity_id`.

- [ ] **Step 1: Create `home-assistant-amb/config/sensor/tesla_energy.yaml`**

This file is automatically picked up by the existing `sensor: !include_dir_merge_list sensor/` include in `configuration.yaml` — no other file needs editing for this task.

```yaml
- platform: integration
  source: sensor.tesla_charger_power_at_home
  name: Tesla Energy Charged At Home
  unique_id: tesla_energy_charged_at_home
  unit_time: h
  round: 2
  max_sub_interval:
    minutes: 1
```

Notes for the implementer:
- This mirrors the existing style in `home-assistant-amb/config/sensor/illuminance.yaml` and `sensor/washing_machine.yaml` (a top-level list with a `platform:` key), just a different platform (`integration` — Home Assistant's built-in Riemann-sum helper — instead of `filter`).
- The source sensor's unit is already `kW`; with `unit_time: h` and no `unit_prefix` set, the result is `kW * h = kWh` directly. Do NOT add `unit_prefix: k` here — the source is already in the "kilo" scale, so that would incorrectly divide the result by another 1000.
- Home Assistant auto-derives `device_class: energy` for this sensor because its source has `device_class: power` and the resulting unit is `kWh` — do not set `device_class` explicitly; the `integration` platform's config schema does not accept it and `just test` would fail on an unknown key.
- `max_sub_interval: {minutes: 1}` forces the integral to keep accumulating (or correctly stop accumulating) at least once a minute even if `sensor.tesla_charger_power_at_home` stops emitting new values for a while (e.g. car goes straight to sleep right after a charge session ends) — without it, the sensor only recalculates when its source's state changes.
- This sensor's value survives Home Assistant restarts automatically (built-in behavior of the `integration` platform) — it starts at `0` only once, the very first time this config is loaded.

- [ ] **Step 2: Validate**

Run from `home-assistant-amb/`:
```bash
just build && just test
```
Expected: no error output, command exits `0`.

- [ ] **Step 3: Commit**

```bash
git add home-assistant-amb/config/sensor/tesla_energy.yaml
git commit -m "feat(ha): add Tesla home charging energy Riemann-sum sensor"
```

---

### Task 4: Add the Tesla view to the Power dashboard + Overview teaser

**Estimated Task Complexity:** low

**Files:**
- Modify: `home-assistant-amb/config/dashboard/power.yaml:159` (append a new view at end of file)
- Modify: `home-assistant-amb/config/dashboard/overview.yaml:396` (append a new subheader + tile at end of file)

**Interfaces:**
- Consumes: `sensor.tesla_energy_charged_at_home` (Task 3), `sensor.tesla_charger_power` (Task 1), `sensor.tesla_battery_level` (pre-existing).

- [ ] **Step 1: Append a new "Tesla" view to `home-assistant-amb/config/dashboard/power.yaml`**

Current end of file (lines 150-159):

```yaml
            entity: sensor.climate_fridge_temperature
            icon: mdi:fridge
          - type: history-graph
            title: "Fridge temperature (12h)"
            entities:
              - entity: sensor.climate_fridge_temperature
                name: Fridge
              - entity: input_number.fridge_temperature_threshold
                name: Thr.
            hours_to_show: 12
```

Change to (append a new top-level view after the `Appliances` view, at the same indentation as the other `- title:` view entries):

```yaml
            entity: sensor.climate_fridge_temperature
            icon: mdi:fridge
          - type: history-graph
            title: "Fridge temperature (12h)"
            entities:
              - entity: sensor.climate_fridge_temperature
                name: Fridge
              - entity: input_number.fridge_temperature_threshold
                name: Thr.
            hours_to_show: 12
  - title: Tesla
    path: tesla
    icon: mdi:car-electric
    type: sections
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Tesla charging
            heading_style: title
            icon: mdi:car-electric
          - type: tile
            entity: sensor.tesla_energy_charged_at_home
            icon: mdi:car-electric
          - type: tile
            entity: sensor.tesla_battery_level
          - type: history-graph
            title: "Tesla charger power (24h)"
            entities:
              - entity: sensor.tesla_charger_power
                name: Power
            hours_to_show: 24
```

- [ ] **Step 2: Append a matching "Tesla" subheader + teaser to `home-assistant-amb/config/dashboard/overview.yaml`**

Current end of file (lines 382-396, end of the Power section's Appliances teaser):

```yaml
          - type: heading
            heading: Appliances
            heading_style: subtitle
            icon: mdi:washing-machine
            tap_action:
              action: navigate
              navigation_path: /dashboard-power/appliances
          - type: tile
            entity: sensor.washing_machine_state
            icon: mdi:washing-machine
          - type: history-graph
            entities:
              - entity: sensor.washing_machine_state
                name: WM
            hours_to_show: 12
```

Change to (append a new subheader + one teaser tile, keeping it after Appliances so subheader order still matches the Power dashboard's view order: Grid, Plugs, Appliances, Tesla):

```yaml
          - type: heading
            heading: Appliances
            heading_style: subtitle
            icon: mdi:washing-machine
            tap_action:
              action: navigate
              navigation_path: /dashboard-power/appliances
          - type: tile
            entity: sensor.washing_machine_state
            icon: mdi:washing-machine
          - type: history-graph
            entities:
              - entity: sensor.washing_machine_state
                name: WM
            hours_to_show: 12
          - type: heading
            heading: Tesla
            heading_style: subtitle
            icon: mdi:car-electric
            tap_action:
              action: navigate
              navigation_path: /dashboard-power/tesla
          - type: tile
            entity: sensor.tesla_energy_charged_at_home
            icon: mdi:car-electric
```

Notes for the implementer:
- `/dashboard-power/tesla` matches the `dashboard-power` dashboard key (`home-assistant-amb/config/lovelace.yaml`) plus the new view's `path: tesla` from Step 1 — same pattern as the existing `/dashboard-power/grid`, `/dashboard-power/plugs`, `/dashboard-power/appliances` links right above it.
- No changes needed to `home-assistant-amb/config/lovelace.yaml` — this is a new view inside the existing `dashboard-power` dashboard file, not a new dashboard.

- [ ] **Step 3: Validate**

Run from `home-assistant-amb/`:
```bash
just test
```
Expected: no error output, exits `0`. Note: `check_config` validates the YAML is well-formed and matches the `lovelace:` schema, but doesn't deeply validate every card/badge field — visually confirm the new tab and tiles after deploying (Task 5).

- [ ] **Step 4: Commit**

```bash
git add home-assistant-amb/config/dashboard/power.yaml home-assistant-amb/config/dashboard/overview.yaml
git commit -m "feat(ha): add Tesla view to Power dashboard"
```

---

### Task 5: Document, deploy, register on the Energy dashboard, and verify

**Estimated Task Complexity:** low

**Files:**
- Modify: `CLAUDE.md:71-73` (insert one new subsection after "Dashboard Conventions")

**Interfaces:**
- Consumes: `sensor.tesla_energy_charged_at_home` (Task 3).

- [ ] **Step 1: Document that the Energy dashboard's device list is UI-managed**

Current lines 65-73 of `CLAUDE.md`:

```markdown
### Dashboard Conventions

Lovelace dashboards (`dashboard/*.yaml`) follow these conventions:

- **Titles** (`heading_style: title`) = section names. They are never links and need no corresponding dashboard page — they organize local content within a view.
- **Subheaders** (`heading_style: subtitle`) = view names. Subheaders tap-link directly to that view's page.
- **View order** in a sub-dashboard (Power, Lights, Climate) must match the order the corresponding subheaders appear on the Overview dashboard, so the sidebar tab order mirrors the overview.

### Zigbee2MQTT Device Renames
```

Change to (insert a new subsection between "Dashboard Conventions" and "Zigbee2MQTT Device Renames"):

```markdown
### Dashboard Conventions

Lovelace dashboards (`dashboard/*.yaml`) follow these conventions:

- **Titles** (`heading_style: title`) = section names. They are never links and need no corresponding dashboard page — they organize local content within a view.
- **Subheaders** (`heading_style: subtitle`) = view names. Subheaders tap-link directly to that view's page.
- **View order** in a sub-dashboard (Power, Lights, Climate) must match the order the corresponding subheaders appear on the Overview dashboard, so the sidebar tab order mirrors the overview.

### Energy Dashboard

The built-in Home Assistant Energy dashboard (grid source, "Individual devices" list, and the "Energy flow" Sankey chart) is configured entirely via **Settings → Dashboards → Energy** in the UI and stored in `.storage/energy` — it is not represented anywhere in this repo's YAML. To make a new sensor appear in the Energy flow chart, first deploy the entity (as YAML, via the normal flow), then manually add it as an Individual Device in that UI. Energy-tracking sensors should have `device_class: energy`, a `kWh`/`Wh`/`MWh` unit, and a `total` or `total_increasing` state class (see e.g. `sensor.tesla_energy_charged_at_home`, built from the `integration` platform in `config/sensor/tesla_energy.yaml`).

### Zigbee2MQTT Device Renames
```

- [ ] **Step 2: Validate and commit**

Run from `home-assistant-amb/`:
```bash
just test
```
Expected: no error output, exits `0` (this step only touches a `.md` file, but re-running confirms nothing else broke).

```bash
git add CLAUDE.md
git commit -m "docs: document Energy dashboard is UI-managed, not YAML"
```

- [ ] **Step 3: Push the branch**

```bash
git push -u origin feat/tesla-home-charging-energy
```
Expected: branch pushed, GitHub Actions workflow that validates `home-assistant-amb/**` runs and passes (same `just build`/`just test` steps).

- [ ] **Step 4: Deploy to the Raspberry Pi**

This is a config-only change (no `Dockerfile` or image tag edit), so no image rebuild is needed. Tell the user to run, on the Pi, in `home-assistant-amb/`:
```bash
git fetch
git checkout feat/tesla-home-charging-energy
```
Then reload Home Assistant's YAML configuration from the UI (Developer Tools → YAML → Reload All, or Settings → System → Restart if a full restart is preferred — a restart is safer here since it's the first time the `integration` platform sensor is created).

- [ ] **Step 5: Verify the new entities**

In Home Assistant, go to **Developer Tools → States** and check each of these (filter by `tesla`):
- `sensor.tesla_charger_power` — numeric, `kW`, changes when charging (any location).
- `sensor.tesla_geofence` — text, reads `Home` when the car is actually at home.
- `sensor.tesla_charger_power_at_home` — numeric, `kW`, equals `tesla_charger_power` only while `tesla_geofence` is `Home`, otherwise `0`.
- `sensor.tesla_energy_charged_at_home` — numeric, `kWh`, starts at `0` and only increases while `tesla_charger_power_at_home` is above `0`.

If any read `unavailable`, check that `teslamate/cars/1/healthy` is publishing `true` (TeslaMate UI on port `4000` should show the car online, not erroring).

- [ ] **Step 6: Register the entity on the Energy dashboard**

In Home Assistant: **Settings → Dashboards → Energy**. Under **"Home Assistant Devices"** (Individual devices) section, click **"Add Device"**, pick `sensor.tesla_energy_charged_at_home` from the list, and **Save**. This is the one-time manual step (config lives in `.storage/energy`, not this repo) that actually makes Tesla home charging appear as a branch under "Home" in the "Energy flow" Sankey chart shown on the main Energy dashboard.

- [ ] **Step 7: Verify the dashboards**

- Open the **Power** dashboard (sidebar) and confirm a new **Tesla** tab appears after **Appliances**, showing the energy-charged-at-home tile, battery level tile, and a 24h charger power graph.
- Open the **Overview** dashboard and confirm a new **Tesla** subheader appears in the Power section, after Appliances, linking to the new tab.
- After the Tesla has charged at home at least once since deploying, open the main **Energy** dashboard and confirm a "Tesla Energy Charged At Home" (or similar, based on the friendly name) branch appears under "Home" in the Energy flow chart, and that it stays flat (no growth) if/when the car charges away from home instead.

- [ ] **Step 8: Open a PR**

```bash
gh pr create --base main --head feat/tesla-home-charging-energy --title "feat(ha): show Tesla home charging in Energy dashboard" --body "Adds TeslaMate charger power + geofence MQTT sensors, a home-gating template sensor, and a Riemann-sum kWh sensor for Tesla home charging. Adds a new Tesla view to the Power dashboard + matching Overview teaser. Manual step required after merge: register sensor.tesla_energy_charged_at_home on the Energy dashboard (Settings > Dashboards > Energy > Add Device) — see CLAUDE.md's new Energy Dashboard section."
```
Expected: PR created; once CI passes and the manual verification in Steps 5-7 is done, merge and delete the branch.
