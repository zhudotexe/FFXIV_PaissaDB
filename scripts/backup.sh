#!/bin/bash
# Dump the DB to stdout with maximum compression, and stream that to S3

sudo -u paissadb pg_dump --no-owner -v -Z 9 paissadb | aws s3 cp - s3://paissadb-historical/paissadb-${timestamp}.sql.gz
