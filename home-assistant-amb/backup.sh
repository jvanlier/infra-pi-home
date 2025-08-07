#!/usr/bin/env bash
set -eux

PATH=$PATH:/usr/local/bin:/bin

DATE=$(date +%Y-%m-%d)
DATE_DELETE=$(date -d '-3 months' +%Y-%m-%d)
FN_PREFIX=home_assistant_amb_dump
FN=${FN_PREFIX}_${DATE}.tar
FN_DELETE=${FN_PREFIX}_${DATE_DELETE}.tar

echo "Date now: ${DATE}, filename now: ${FN}"
echo "Date to delete: ${DATE_DELETE}, filename to delete: ${FN_DELETE}"

docker-compose stop
sudo tar cvf ${FN} config/
sudo chown jori:jori ${FN}
pbzip2 ${FN}
docker-compose up -d

aws s3 cp ${FN}.bz2 s3://jvl-bak
rm ${FN}.bz2
aws s3 rm s3://jvl-bak/${FN_DELETE}
