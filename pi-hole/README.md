pi-hole
======

Setup:

```
mkdir -p var-log
touch var-log/pihole.log
```

Create `.env` file with WEBPASSWORD.

Webinterface will run on port 8001 (http) because 80 is already taken by Traefik in TeslaMate.
