Samba fileshare
=============

Sharing some media using Samba - not in docker.

Update: actually, not quite sure if unix user `media` needs to be added since we also add the SMB user.

```bash
sudo adduser media
mkdir -p /media
sudo chown media:media /media

sudo apt-get install samba samba-common-bin
```

Add the following to `/etc/samba/smb.conf` and remove the default share definitions:

```
[pi-share]
path = /media
browseable = yes
read only = yes
guest ok = no
valid users = media
```


### Mac Time Machine backup

Create a dedicated, writable directory and account rather than reusing the read-only media share:

```bash
sudo adduser --disabled-password --gecos "" time-machine
sudo install -d -o time-machine -g time-machine -m 0700 /srv/time-machine
sudo smbpasswd -a time-machine
```

Add this second share to `/etc/samba/smb.conf`:

```
[time-machine]
path = /srv/time-machine
browseable = yes
read only = no
guest ok = no
valid users = time-machine
vfs objects = catia fruit streams_xattr
fruit:time machine = yes
```

Use `time-machine` and its SMB password when selecting the network disk in macOS Time Machine.

Validate the complete configuration, then restart Samba:

```bash
sudo testparm
sudo systemctl restart smbd
```
