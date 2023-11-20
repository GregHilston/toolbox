#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Downloads a youtube URL as an MP3 file

youtube-dl --extract-audio --audio-format mp3 $1
