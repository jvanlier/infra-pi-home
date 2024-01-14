#!/usr/bin/env bash
set -eux

DATE=$(date +%Y-%m-%d)
FN=hass_dump_${DATE}.tar.bz2
PATH=$PATH:/home/pi/.local/bin:/usr/local/bin:/bin

# FIXME: too native, tar exists if file is changed during execution. DB file gets changed constantly.
# Look into native backup functionality: https://www.home-assistant.io/common-tasks/supervised/#alternative-creating-a-backup-using-the-home-assistant-command-line-interface
tar cvjSf ${FN} config
aws s3 cp ${FN} s3://jvl-bak
rm ${FN}

DATE_TO_DELETE=$(date -d "-3 months" +%Y-%m-%d)
FN_TO_DELETE=hass_dump_${DATE_TO_DELETE}.tar.bz2
aws s3 rm s3://jvl-bak/${FN_TO_DELETE}
