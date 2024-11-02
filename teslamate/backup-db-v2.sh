#!/usr/bin/env bash
set -eux

PATH=$PATH:/usr/local/bin:/bin

DATE=$(date +%Y-%m-%d)
DATE_DELETE=$(date -d '-3 months' +%Y-%m-%d)
FN_PREFIX=teslamate_dump
FN=${FN_PREFIX}_${DATE}.bck
FN_DELETE=${FN_PREFIX}_${DATE_DELETE}.bck

docker-compose exec -T database pg_dump -U teslamate teslamate > ${FN}
# Parallel bzip2:
pbzip2 ${FN}

aws s3 cp ${FN}.bz2 s3://jvl-bak
rm ${FN}.bz2
aws s3 rm s3://jvl-bak/${FN_DELETE}

