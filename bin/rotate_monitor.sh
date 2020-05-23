#!/bin/bash
# This is a script that toggles rotation of the screen through xrandr,
# and also toggles rotation of the stylus, eraser and cursor through xsetwacom

# Check orientation
orientation=`/usr/bin/xrandr --verbose -q | grep LVDS | awk '{print $6}'`
# Rotate the screen and stylus, eraser and cursor, according to your preferences.
if [ "$1" = "normal" ]; then
    if [ "$orientation" = "normal" ]; then
	/usr/bin/xrandr --output LVDS-1 --rotate right
	/usr/bin/xsetwacom set 14 Rotate cw
	/usr/bin/xsetwacom set 15 Rotate cw
	/usr/bin/xsetwacom set 16 Rotate cw
    else
	/usr/bin/xrandr --output LVDS-1 --rotate normal
	/usr/bin/xsetwacom set 14 Rotate none
	/usr/bin/xsetwacom set 15 Rotate none
	/usr/bin/xsetwacom set 16 Rotate none
    fi
elif [ "$1" = "invert" ]; then
    if [ "$orientation" = "normal" ]; then
	/usr/bin/xrandr --output LVDS-1 --rotate inverted
	/usr/bin/xsetwacom set 14 Rotate half
	/usr/bin/xsetwacom set 15 Rotate half
	/usr/bin/xsetwacom set 16 Rotate half
    elif [ "$orientation" = "inverted" ]; then
	/usr/bin/xrandr --output LVDS-1 --rotate normal
	/usr/bin/xsetwacom set 14 Rotate none
	/usr/bin/xsetwacom set 15 Rotate none
	/usr/bin/xsetwacom set 16 Rotate none
    elif [ "$orientation" = "right" ]; then
	/usr/bin/xrandr --output LVDS-1 --rotate left
	/usr/bin/xsetwacom set 14 Rotate ccw
	/usr/bin/xsetwacom set 15 Rotate ccw
	/usr/bin/xsetwacom set 16 Rotate ccw
    elif [ "$orientation" = "left" ]; then
	/usr/bin/xrandr --output LVDS-1 --rotate right
	/usr/bin/xsetwacom set 14 Rotate cw
	/usr/bin/xsetwacom set 15 Rotate cw
	/usr/bin/xsetwacom set 16 Rotate cw
    fi
fi

