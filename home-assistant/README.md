Home Assistant
==============

The config directory is gitignored, but it should probably be backed up. It also contains the data.

**TODO: backup config dir**

The file `config/configuration.yaml` looks like something we'd like to place in Git, however it currently also contains secrets related to the Nest integration.

## Adaptive Lightning
The Docker install disallows add-on installations. But add-ons can be installed manually:

```bash
git clone --max-depth 1 https://github.com/basnijholt/adaptive-lighting
sudo mkdir -p config/custom_components
sudo mv adaptive-lightning/custom_components/adaptive_lightning config/custom_components/
```
Using sudo because unfortunately HASS runs as root in the stock Docker image, and so the config dir is owned by root.

Curently using hash `83983e85fc2cc91d2c47bf0c018a34a1f2b7ab8f` from Dec 16, 2021 with HASS 2022.2.6.
Seems to work fine, but some Python errors in the logs.

