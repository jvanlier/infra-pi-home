teslamate
=========

Source: https://docs.teslamate.org/docs/installation/docker

Using the simple installation method because the UIs are not exposed to the internet.

Setup the .env and .htpasswd files locally following the instructions in the teslamate docs.

Crontab entry for backups:

```
42 3 1 * * cd /home/jori/infra-pi-home/teslamate && ./backup-db-v2.sh
```

NOTE: data is stored in Docker volume, not in the infra-pi-home dir.
When you reinstall, be sure to grab a fresh dump first. Otherwise you may lose some data if you go by the monthly dumps on AWS.
This happened once: data for 2023-09-01 - 2023-09-21 was lost.
