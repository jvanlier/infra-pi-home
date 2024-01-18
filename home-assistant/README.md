Home Assistant
==============

**TODO: backup config dir**

## Adaptive Lightning
The Docker install disallows add-on installations. But add-ons can be installed manually:

```bash
git clone --depth 1 https://github.com/basnijholt/adaptive-lighting
sudo mkdir -p config/custom_components
sudo mv adaptive-lightning/custom_components/adaptive_lightning config/custom_components/
```
Using sudo because unfortunately HASS runs as root in the stock Docker image, and so the config dir is owned by root.

## mini-graph-card
Download and copy `mini-graph-card-bundle.js` from the [latest](https://github.com/kalkih/mini-graph-card/releases/latest) release into your `config/www` directory.

```bash
curl -OL https://github.com/kalkih/mini-graph-card/releases/download/v0.11.0/mini-graph-card-bundle.js
mkdir -p config/www
mv mini-graph-card-bundle.js config/www/
```

## average sensor
```bash
cd custom_components/
mkdir average
cd average/
curl -OL https://github.com/Limych/ha-average/releases/download/2.3.0/average.zip
unzip average.zip
rm average.zip
```

## apex chart
```bash
cd config/www
curl -OL https://github.com/RomRider/apexcharts-card/releases/download/v2.0.1/apexcharts-card.js
```

## lovelace-mushroom
cd config/www
curl -OL https://github.com/piitaya/lovelace-mushroom/releases/download/v2.4.1/mushroom.js

## Motion Sensor setup

Usually, lights for PIR sensors should be on for at least 180 seconds / 3 minutes.
This is because PIR sensors don't detect non-moving objects, and 180 seconds feels just about right for high traffic areas to prevent lights from going off when you're standing still.

Exceptions:

- toilets and bathrooms: 420 s / 7 mins
- dressing room: 120 s is sufficient
- hall: 20 s to get quick activation of proximity activated lights in living room / kicthen after turning everything off and going into the hallway.

The sensors I use have a configurable occupancy timeout (Frient Motion Sensor Pro) / detection interval (Aqara P1).
(Same thing, different name).

However, it can be tricky to set them to a high value.
It may fail and "brick" the device temporarily, fixed with a factory reset.
However, things have gotten better after OTA upgrading them.

Generally, I prefer to set them to as high as possible to:

- limit zigbee traffic and possibly battery use
- limit HA logbook spam

Taking into account device limitations:

- Aqara P1 max is 200 according to its specs.
- Not sure about Frients, the max I've tried so far is 180 (and in one case 180 didn't work but 179 did...)

When two or more sensors control one light, it makes sense to set them to the same value, but it's not required - I'm handling that with template sensors to pick the lowest value across all sensors.
