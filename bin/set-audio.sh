#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

pactl set-default-source 'alsa_input.usb-046d_0809_C5639C62-02.mono-fallback'
pactl set-default-sink 'alsa_output.usb-Blue_Microphones_Yeti_Stereo_Microphone_REV8-00.analog-stereo'
