#!/bin/bash
# Animate a tmux overlay image by cycling through pre-converted .six frame files.
# Usage: animate-overlay.sh X Y FRAMES_DIR [FPS]
#   X Y        — cell coordinates for overlay-image set
#   FRAMES_DIR — directory containing frame_00.six, frame_01.six, ...
#   FPS        — frames per second (default: 12)
#
# To stop: kill the process and run: tmux overlay-image clear

set -e

X="${1:?Usage: animate-overlay.sh X Y FRAMES_DIR [FPS]}"
Y="${2:?}"
FRAMES_DIR="${3:?}"
FPS="${4:-12}"

DELAY=$(echo "scale=4; 1/$FPS" | bc)
frames=("$FRAMES_DIR"/frame_*.six)
nframes=${#frames[@]}

if [ "$nframes" -eq 0 ]; then
    echo "No .six files found in $FRAMES_DIR" >&2
    exit 1
fi

i=0
while true; do
    tmux overlay-image set "$X" "$Y" "${frames[$i]}"
    i=$(( (i + 1) % nframes ))
    sleep "$DELAY"
done
