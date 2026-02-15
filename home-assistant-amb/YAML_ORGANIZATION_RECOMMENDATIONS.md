# YAML Organization Recommendations

## Current Strengths

1. **Split configuration pattern** - Using `!include_dir_merge_list` for automations, sensors, and templates is excellent for maintainability
2. **Semantic file naming** - Files like `light_motion_activated_dark_aware.yaml`, `presence.yaml`, `dark.yaml` clearly indicate their purpose
3. **Dashboard separation** - Moving dashboard configs to `dashboard/` subdirectory keeps things organized
4. **Custom component configs separated** - `adaptive_lighting.yaml` and `illuminance.yaml` are appropriately at root level

## Recommended Improvements

### 1. Split `script.yaml` into directory

You have a TODO comment about script blueprints. Similar to automations, consider:

```yaml
# In configuration.yaml
script: !include_dir_merge_named script/
```

Then create individual files like:
- `script/light_kitchen_dimmed.yaml` (can combine related kitchen scripts)
- `script/wake_up_light_kids.yaml`

This makes scripts easier to find and edit.

### 2. Split `input_boolean.yaml`, `input_datetime.yaml`, `input_number.yaml`

These will grow over time. Consider grouping by function:
```yaml
input_boolean: !include_dir_merge_named input_boolean/
```

Then organize as:
- `input_boolean/sleep_mode.yaml`
- `input_boolean/wake_up_lights.yaml`
- `input_boolean/heating.yaml`

### 3. Consider splitting `binary_sensor.yaml`

It's currently empty, but when you add binary sensors outside of templates, you could use:
```yaml
binary_sensor: !include_dir_merge_list binary_sensor/
```

### 4. Group automation files by domain

You have 30+ automation files. Consider subdirectories:
```
automation/
  light/
    bedroom_duco.yaml
    kitchen.yaml
    living.yaml
  heating/
    bedroom_jc.yaml
    living.yaml
  power/
    power.yaml
  ...
```

Then use: `automation: !include_dir_merge_list automation/`

This pattern recursively includes subdirectories.

### 5. Consider splitting large config files

If `adaptive_lighting.yaml` (3310 bytes) continues growing with more rooms, you could split it:
```yaml
adaptive_lighting: !include_dir_merge_list adaptive_lighting/
```

With files like `adaptive_lighting/bedroom_duco.yaml`, `adaptive_lighting/kitchen.yaml`, etc.

### 6. Add a `packages/` pattern for related entities

For tightly coupled entities (like wake-up lights that span automations, scripts, and input booleans), consider Home Assistant's package feature:

```yaml
homeassistant:
  packages: !include_dir_named packages/
```

Then create `packages/wake_up_lights_kids.yaml` containing all related entities in one file.

## Priority Order

1. **High priority**: Split `script.yaml` into directory (matches your TODO)
2. **Medium priority**: Add automation subdirectories (you have 30+ files)
3. **Low priority**: Split input helpers when they grow beyond 20-30 lines

## Notes

Your current structure is working well. Focus on the script split first since you already identified it as a TODO.
