zigbee2mqtt
===========

Default conf changed to use 1884 for mqtt rather than 1883, because 1883 was already in use.

Web interface available on port 8002.

Copy `zigbee2mqtt-data/configuration.template.yaml` to `zigbee2mqtt-data/configuration.yaml`. 
Not adding the actual configuration to version control, because it writes the network key into the config on start.

Use device from `/dev/serial/by-id` in the config. 
To enable that, we mount `/dev:dev`. 

On the Home Assistant side, just enable the default MQTT integration (change port to 1884) and it should automatically pickup devices. 

HA also has native Zigbee support, but support seems to be limited. Aqara EU Smart Plug only has On/Off and temp, for instance, not power metering. 
Works fine via Zigbee2MQTT.
It's also kind of nice to decouple Zigbee from HA, because HA gets restarted pretty often and that would drop the Zigbee network every time.

