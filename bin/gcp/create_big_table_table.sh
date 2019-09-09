#!/usr/bin/env bash
set -e

# example ./create_big_table_table.sh user-tracking-228117 analytics frontend_test

gcloud config set project $1
cbt -instance $2 createtable $3
cbt -instance $2 createfamily $3 data
cbt -instance $2 createfamily $3 date