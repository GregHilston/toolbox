#!/usr/bin/env bash
set -e

# example ./read_big_table_table.sh user-tracking-228117 analytics frontend_test

gcloud config set project $1
cbt -project $1 -instance $2 read $3