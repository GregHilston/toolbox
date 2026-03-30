#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Diagnose and fix a hung OrbStack Docker daemon

TIMEOUT_SECONDS=5

# Portable timeout function for macOS
check_docker() {
    docker ps &>/dev/null &
    local pid=$!
    local count=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 1
        ((count++))
        if ((count >= TIMEOUT_SECONDS)); then
            kill "$pid" 2>/dev/null || true
            return 1
        fi
    done
    wait "$pid"
}

echo "Checking Docker responsiveness..."

if check_docker; then
    echo "Docker is responsive. No fix needed."
    exit 0
fi

echo "Docker is not responding. Checking OrbStack status..."

if ! pgrep -q OrbStack; then
    echo "OrbStack is not running. Starting it..."
    open -a OrbStack
    sleep 5
    echo "OrbStack started."
    exit 0
fi

echo "OrbStack is running but Docker is hung."
echo "Force-killing OrbStack..."

killall OrbStack || true
sleep 2

echo "Restarting OrbStack..."
open -a OrbStack

echo "Waiting for OrbStack to initialize..."
sleep 5

echo "Checking if Docker is responsive..."
if check_docker; then
    echo "Success! Docker is now responsive."
else
    echo "Docker is still not responding. You may need to wait longer or investigate further."
    exit 1
fi
