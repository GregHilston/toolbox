#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# can use `$ pactl list sources` or `$ pactl list sinks` to know what to set to
# In a pinch, can use the `$ pavucontrol` GUI

# pactl set-default-source 'alsa_input.usb-046d_0809_C5639C62-02.mono-fallback'
pactl set-default-source 'alsa_output.usb-GeneralPlus_USB_Audio_Device-00.analog-stereo.monitor'
pactl set-default-sink 'alsa_output.usb-Blue_Microphones_Yeti_Stereo_Microphone_REV8-00.analog-stereo'
