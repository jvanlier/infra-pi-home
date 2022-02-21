unifi
=====

Using image from https://hub.docker.com/r/linuxserver/unifi-controller

N.b.:
- The inform host is overridden to the ip of the host machine in the configuration as per the instructions in the Dockerhub link.

The config dir is `.gitignored`. Last migration (2022-01) was done using web UI: export backup, in new instance during setup wizard restore from backup. Worked like a charm. But maybe copying the config dir also works.
