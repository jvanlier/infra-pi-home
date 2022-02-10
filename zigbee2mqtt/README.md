zigbee2mqtt
===========

Default conf changed to use 1884 for mqtt rather than 1883, because 1883 was already in use.

Web interface available on port 8002.

Copy `zigbee2mqtt-data/configuration.template.yaml` to `zigbee2mqtt-data/configuration.yaml`. 
It writes the network key into the config on start, rather not have that in git.

On the Home Assistant side, just enable the default MQTT integration (change port to 1884) and it should automatically pickup devices. 
