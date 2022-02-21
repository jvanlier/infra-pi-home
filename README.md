# infra-pi-home


## Ports used on host

- 53 TCP: pi-hole DNS
- 53 UDP: pi-hole DNS
- 80 TCP: TeslaMate treafik
- 443 TCP: TeslaMate traefik
- 1883 TCP: TeslaMate mqtt
- 1884 TCP: zigbee2mqtt mqtt
- 1900 ?: Home Assistant
- 3478 UDP: Unifi controller (STUN service)
- 5514 UDP: Unifi controller (Remote syslog capture)
- 6789 TCP: Unifi controller (Speed Test)
- 8001 TCP: pi-hole web interface (HTTP)
- 8002 TCP: zigbee2mqtt web interface
- 8080 TCP: Unifi controller web interface
- 8123 TCP: Home Assistant web interface
- 8443 TCP: Unifi controller web interface
- 8843 TCP: Unifi controller (HTTPS portal redirection - do we need this?)
- 8880 TCP: Unifi controller (HTTP portal redirection - do we need this?
- 9001 TCP: zigbee2mqtt mqtt over WebSockets
- 10001 UDP: Unifi controller (service discovery)

N.b.: Home Assistant runs in privileged mode, no ports need to be forwarded explictly. 
The list of ports above is not exhaustive for Home Assistant, just what I happened to know of.

