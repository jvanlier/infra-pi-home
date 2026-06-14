zigbee2mqtt using USB
===========

Default conf changed to use 1884 for mqtt rather than 1883, because 1883 was already in use.

Web interface available on port 8002.

On the Home Assistant side, just enable the default MQTT integration (change port to 1884) and it should automatically pickup devices.
