---
name: apexcharts-home-assistant
description: Use when editing Home Assistant Lovelace custom:apexcharts-card YAML in this repo, especially dashboard/climate.yaml or dashboard/overview.yaml.
---

# Apexcharts Home Assistant

Use this skill before editing `custom:apexcharts-card` cards in `home-assistant-amb/config/dashboard/*.yaml`.

## Local Version

- This repo bakes `apexcharts-card.js` into the Home Assistant image from `home-assistant-amb/docker/Dockerfile`.
- Current pinned version: `APEXCHARTS_CARD_VERSION=v2.1.2`.
- Do not assume options from latest apexcharts-card docs are available.
- If changing card features, check `home-assistant-amb/docker/Dockerfile` first for pinned version.

## Known Working Pattern

Existing working cards in this repo use this shape:

```yaml
- type: custom:apexcharts-card
  apex_config:
    chart:
      height: 400px
  header:
    title: Inside versus outside temperature
    show: true
    show_states: true
    colorize_states: true
  graph_span: 32h
  hours_12: false
  all_series_config:
    stroke_width: 3
    fill_raw: last
  series:
    - entity: sensor.example
      name: Example
      extend_to: now
      color: "#009688"
      opacity: 0.9
      type: line
```

Prefer staying close to this pattern unless there is a tested reason to diverge.

## Section View Quirks

- Home Assistant dashboard `type: sections` supports `grid_options` for normal cards.
- `custom:apexcharts-card` v2.1.2 does strict config validation and does not support `section_mode`.
- `section_mode` was added in apexcharts-card v2.2.0.
- In v2.1.2, adding `section_mode: true` causes a red `Configuration error` card.
- In v2.1.2, using `grid_options` on `custom:apexcharts-card` also causes a red `Configuration error` card because section layout support depends on `section_mode`.
- Therefore, for this repo's pinned v2.1.2, do not put `section_mode` or `grid_options` on apexcharts cards.

## Series Options

- `stroke_dash` is supported in apexcharts-card v2.1.2.
- If a new chart still fails after removing unsupported layout keys, test by removing newer/less-used series options next, starting with `stroke_dash`.
- Existing known-good cards use `opacity`, `stroke_width`, `fill_raw`, `extend_to`, `type`, `color`, `unit`, `show`, and `data_generator`.

## Validation Limits

- `just test` validates Home Assistant YAML/config, but it does not fully validate frontend custom-card schemas rendered in the browser.
- A card can pass `just test` and still fail in Lovelace with a red `Configuration error`.
- When fixing frontend-card errors, compare directly against existing rendered cards in the same repo and pinned custom-card version.

## Debug Workflow

1. Read `home-assistant-amb/docker/Dockerfile` to confirm `APEXCHARTS_CARD_VERSION`.
2. Compare against existing working cards in `home-assistant-amb/config/dashboard/overview.yaml` and `home-assistant-amb/config/dashboard/climate.yaml`.
3. Remove unsupported or unproven options first, especially `section_mode` and `grid_options` on v2.1.2.
4. Run `just test` from `home-assistant-amb/` for YAML/config validation.
5. Ask user to reload Lovelace/browser view to confirm runtime rendering.
