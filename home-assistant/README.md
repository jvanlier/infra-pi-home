Home Assistant
==============

**TODO: backup config dir**

## Adaptive Lightning
The Docker install disallows add-on installations. But add-ons can be installed manually:

```bash
git clone --max-depth 1 https://github.com/basnijholt/adaptive-lighting
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

