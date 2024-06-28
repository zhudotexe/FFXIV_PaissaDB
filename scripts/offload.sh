#!/bin/bash
# Dump the plots and events tables to stdout with maximum compression, and stream that to S3
# compression 3/9 is used because holy cpu usage batman
# cronjobbed to run daily at 7:15am UTC to avoid primetimes, only if disk usage > 50%
# cron: 15 7 * * * bash scripts/offload.sh
# shellcheck disable=SC2181

diskUsage=$(printf "%d" $(df --output=pcent . | tail +2 | sed s/%//g))
timestamp=$(date +%s)
dir=$(dirname "$0")

if [[ $diskUsage -lt 50 ]]; then
  echo "Disk usage is at ${diskUsage}%, skipping offload"
  exit 0
fi

# dump, upload to s3
sudo -u paissadb pg_dump --schema-only --no-owner -v -Z 9 paissadb | aws s3 cp - s3://paissadb-historical/paissadb-schema-${timestamp}.sql.gz
sudo -u paissadb pg_dump --data-only --no-owner -t plot_states -t events -v -Z 3 paissadb | aws s3 cp - s3://paissadb-historical/paissadb-data-${timestamp}.sql.gz

# if the upload succeeded, delete data older than 1 week
if [[ $? == 0 ]]; then
  paissaHome=$(eval echo "~paissadb")  # mild hack but whatever
  cp ${dir}/delete_1w.sql ${paissaHome}/delete_1w.sql
  sudo -u paissadb psql -f ${paissaHome}/delete_1w.sql paissadb
fi
