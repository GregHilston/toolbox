#!/usr/bin/env bash
set -e

gcloud config set project $1
cbt -instance $2 createtable $3
cbt -instance $2 createfamily $3 data
cbt -instance $2 createfamily $3 date