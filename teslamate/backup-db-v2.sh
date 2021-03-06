#!/usr/bin/env bash
set -eux

DATE=$(date +%Y-%m-%d)
FN=teslamate_dump_${DATE}.bck
PATH=$PATH:/home/pi/.local/bin:/usr/local/bin:/bin

docker-compose exec -T database pg_dump -U teslamate teslamate > ${FN}
# Parallel bzip2:
pbzip2 ${FN}

aws s3 cp ${FN}.bz2 s3://jvl-bak
rm ${FN}.bz2

