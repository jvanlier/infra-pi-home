Home Assistant
==============

Approach: run official Docker image on Pi.
Add custom extensions manually.
Maintain YAMLs directly on Pi with vim.

Should probably make a custom Docker image at some point, preferably in GHA, run some container-structure-tests, and deploy that.
But time is limited at the moment.

## Backup
Crontab entry for backups:

```
42 4 1 * * cd /home/ubuntu/infra-pi-home/home-assistant && ./backup.sh
```

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
