#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Diagnose and fix a hung OrbStack Docker daemon.
#
# Common cause: macOS clamshell sleep suspends the OrbStack VM, and on wake
# the Docker socket either disappears or the daemon hangs indefinitely.
#
# This script:
#   1. Checks if Docker is responsive (quick path — exits if healthy)
#   2. Force-kills ALL OrbStack processes (including Helper) with SIGKILL
#   3. Waits for processes to fully exit
#   4. Relaunches OrbStack and waits for the Docker socket + daemon to be ready

DOCKER_TIMEOUT=5
KILL_WAIT=5
STARTUP_WAIT=20
DOCKER_SOCKET="$HOME/.orbstack/run/docker.sock"
UNRAID_IP="192.168.1.2"

# Portable timeout function for macOS (no coreutils `timeout` needed)
check_docker() {
  docker ps &>/dev/null &
  local pid=$!
  local count=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1
    ((count++))
    if ((count >= DOCKER_TIMEOUT)); then
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

echo "Docker is not responding."

# Check if Unraid NFS server is reachable — if not, containers will hang on NFS volume mounts
echo "Checking if Unraid server ($UNRAID_IP) is reachable..."
if ! ping -c 1 -W 2 "$UNRAID_IP" &>/dev/null; then
  echo ""
  echo "WARNING: Unraid server ($UNRAID_IP) is NOT reachable!"
  echo ""
  echo "Most containers use NFS volumes mounted from Unraid."
  echo "If Unraid is down, OrbStack will hang waiting for NFS mounts."
  echo ""
  echo "Please power on / check the Unraid server, then run this script again."
  exit 1
fi
echo "Unraid server is reachable."

# Check if NFS exports are available — Unraid may be pingable but still booting
echo "Checking if Unraid NFS exports are ready..."
if ! showmount -e "$UNRAID_IP" &>/dev/null; then
  echo ""
  echo "WARNING: Unraid is reachable but NFS exports are not available yet!"
  echo ""
  echo "Unraid is likely still booting. Wait 1-2 minutes for NFS to initialize,"
  echo "then run this script again."
  echo ""
  echo "To check manually: showmount -e $UNRAID_IP"
  exit 1
fi
echo "Unraid NFS exports are available."
echo "Checking OrbStack status..."

if ! pgrep -i -q orbstack; then
  echo "OrbStack is not running. Starting it..."
  open -a OrbStack
  sleep "$STARTUP_WAIT"
  if check_docker; then
    echo "OrbStack started. Docker is responsive."
    exit 0
  else
    echo "OrbStack started but Docker is still not responding."
    exit 1
  fi
fi

echo "OrbStack is running but Docker is hung."
echo "Force-killing all OrbStack processes (SIGKILL)..."

# SIGKILL all OrbStack-related processes — SIGTERM isn't enough when the VM is wedged
pkill -9 -i orbstack 2>/dev/null || true

echo "Waiting ${KILL_WAIT}s for processes to exit..."
sleep "$KILL_WAIT"

# Verify everything is dead
if pgrep -i -q orbstack; then
  echo "WARNING: Some OrbStack processes survived. Attempting another kill..."
  pkill -9 -i orbstack 2>/dev/null || true
  sleep 3
fi

# Clean up stale socket if it exists (OrbStack recreates it on start)
if [ -e "$DOCKER_SOCKET" ]; then
  echo "Removing stale Docker socket..."
  rm -f "$DOCKER_SOCKET"
fi

echo "Restarting OrbStack..."
open -a OrbStack

echo "Waiting ${STARTUP_WAIT}s for OrbStack to initialize..."
sleep "$STARTUP_WAIT"

# Check for socket first — if it doesn't exist, Docker can't respond
if [ ! -e "$DOCKER_SOCKET" ]; then
  echo "Docker socket not yet created. Waiting another ${STARTUP_WAIT}s..."
  sleep "$STARTUP_WAIT"
fi

echo "Checking if Docker is responsive..."
if check_docker; then
  echo "Success! Docker is now responsive."
else
  echo "Docker is still not responding after restart."
  echo ""
  echo "Try rebooting: sudo reboot"
  exit 1
fi
