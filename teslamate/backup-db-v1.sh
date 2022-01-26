#!/usr/bin/env /bin/bash
# Old backup script used in AWS for a while. Now preferring backup
# method from teslamate docs.
set -eux

CONTAINER_ID=`docker ps -aqf "name=teslamate_database_1"`
FN=/home/ubuntu/teslamate_dump_`date +%Y-%m-%d`.sql

docker exec $CONTAINER_ID /usr/bin/pg_dump -U teslamate -d teslamate > $FN
gzip $FN
aws s3 cp ${FN}.gz s3://jvl-bak
rm ${FN}.gz
