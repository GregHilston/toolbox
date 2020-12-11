#!/bin/bash

cat ~/.aws/credentials | grep 'PROFILE NAME' -A3 | grep '=' | tr -d ' ' | xargs -n1 export
