teslamate
=========

Source: https://docs.teslamate.org/docs/guides/traefik

Setup the .env and .htpasswd files locally following the instructions in the teslamate docs.

Crontab entry for backups:

```
42 3 1 * * cd /home/pi/infra-pi-home/teslamate && ./backup-db-v2.sh
```
