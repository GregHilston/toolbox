#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Directory containing variables files
variables_dir="./ansible/variables"

# Populate supported operating systems based on available files
supported_operating_systems=()

for file in "$variables_dir"/*.yml; do
  # Extract the filename without the path and extension
  os=$(basename "$file" .yml)
  supported_operating_systems+=("$os")
done

# Function to display usage text
display_usage() {
  echo "Error: $1"
  echo "Usage: $0 <operating system (${supported_operating_systems[@]})>"
}

# Check if the required operating system parameter is provided
if [ "$#" -ne 1 ]; then
  display_usage "Missing required operating system parameter."
  exit 1
fi

# Set the operating system variable
OS="$1"

# Validate the supported operating systems
found=false
for supported_os in "${supported_operating_systems[@]}"; do
  if [ "$OS" == "$supported_os" ]; then
    found=true
    break
  fi
done

if [ "$found" == false ]; then
  display_usage "Unsupported operating system '$OS'."
  exit 2
fi

ansible-playbook -i ansible/hosts.ini ansible/playbooks/deploy-$OS.yml
