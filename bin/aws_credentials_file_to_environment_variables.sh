#!/bin/bash

for c in $(cat ~/.aws/credentials | grep 'PROFILE NAME HERE' -A3 | grep '=' | tr -d ' '); do export "$c"; done
