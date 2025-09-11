# Home Assistant Ambacht

## What's inside

My Home Assistant configuration files, a `docker-compose.yml` to run it, a backup script for S3, and a custom Dockerfile that bakes in the custom components that I need.

N.b.: in order to make the baked-in custom components work, the config dir contains a (probably) dead symlink `custom_components > /custom_components`.
This is needed because the custom components must in the config dir, but that dir gets mounted during run, so anything we place there at build time will not be visible at run time.
The symlink makes Home Assistant use the baked-in custom components instead.

## To build

```sh
docker compose build
```

At the end you see the name of the docker image:

```text
[...]
 => => naming to docker.io/library/home-assistant-amb-homeassistant
 ```

## To test

Invoke the Home Assistant config checker locally before trying it on Home Assistant to catch errors as early as possible:

```
docker run --rm -v $(pwd)/config:/config docker.io/library/home-assistant-amb-homeassistant hass --script check_config -c /config
```
