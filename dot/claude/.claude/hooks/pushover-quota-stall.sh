#!/bin/sh
# Notification hook: a usage-limit auto resume stalled.
exec "$HOME/Git/toolbox/bin/pushover.py" -m "Claude auto-resume stalled on $(hostname -s): $(pwd)"
