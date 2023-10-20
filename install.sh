#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

ansible-playbook -i ansible/hosts.ini ansible/playbooks/deploy.yml