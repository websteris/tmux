# overlay-image tools

Utilities for the `overlay-image` tmux command added by this fork.

## overlay-image command

```
tmux overlay-image set X Y FILE [-W cols] [-H rows]
tmux overlay-image animate X Y FILE [-W cols] [-H rows]
tmux overlay-image clear
```

`set` places a static sixel image at screen cell (X, Y). PNG files with alpha
are automatically converted. `animate` loads an animated GIF, WebP, or APNG
and plays it in-place using per-frame durations from the file metadata.

`-W`/`-H` scale to the given number of terminal columns/rows.

## Tools

### png_to_sixel.py
Converts a PNG with alpha channel to sixel format. Transparent pixels
(alpha < 128) use P2=1 — they show existing terminal content through.

```bash
python3 png_to_sixel.py input.png [--width PX] [--height PX] > output.six
```

### animated_to_sixel.py
Extracts frames and per-frame durations from an animated image (GIF, WebP,
APNG) and writes a framed sixel stream consumed by `overlay-image animate`.
Called automatically by the C command — not normally invoked by hand.

```bash
python3 animated_to_sixel.py input.gif [--width PX] [--height PX]
```

### generate_example_frames.py
Generates a 24-frame spinning arc animation as RGBA PNG frames.

```bash
python3 generate_example_frames.py
```

### thinking.gif
Ready-to-use spinning arc animation (24 frames, 40ms/frame):

```bash
tmux overlay-image animate 5 2 tools/thinking.gif -W 8 -H 4
```

## Requirements
- Python 3 with Pillow (`pip install Pillow`)
