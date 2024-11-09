unifi
=====

Using image from https://hub.docker.com/r/linuxserver/unifi-network-application

Git repo: https://github.com/linuxserver/docker-unifi-network-application

## Migration

Download a backup via UI.
It's also possible to take the monthly autobackup in the config dir.

APs are sticky, they don't like it when their controller suddenly changes.
The drama-free way to do it, is to forget the old controller in the UI (after the backup).
Otherwise factory reset (see below).

On the old location:

```sh
docker-compose down
```

Copy gitignored file `.env` to the new location.
Continue there.

```sh
docker-compose up
```

Login to the web UI and restore from backup.

Update integration in Home Assistant.

## AP recovery

Factory reset, hold reset button 10 sec.
Led will flash.
(Hold it too short, and it will merely reboot).

This does not apear to be enough though.
They are still not adoptable through the UI.

ssh into ap with ubnt/ubnt

Run this:

```
mca-cli
set-inform http://x.x.x.x:8080/inform
```

After adopting, ubnt/ubnt will no longer work.
The creds can be found in the UniFI UI.
Store them in a password manager.
