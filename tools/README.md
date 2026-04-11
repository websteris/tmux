# overlay-image tools

Utilities for the `overlay-image` tmux command added by this fork.

## overlay-image command

```
tmux overlay-image set X Y FILE [-W cols] [-H rows]
tmux overlay-image clear
```

Places a sixel image at screen cell (X, Y). PNG files with alpha are
automatically converted using `png_to_sixel.py`. `-W`/`-H` scale the
image to the given number of terminal columns/rows.

## Tools

### png_to_sixel.py
Converts a PNG with alpha channel to sixel format. Transparent pixels
(alpha < 128) use P2=1 — they show the existing terminal content through.

```bash
python3 png_to_sixel.py input.png [--width PX] [--height PX] > output.six
```

### generate_example_frames.py
Generates a spinning arc animation as PNG frames.

```bash
python3 generate_example_frames.py --output-dir ./my-frames --frames 24 --size 120
```

### animate-overlay.sh
Cycles through pre-converted .six frame files to animate the overlay.

```bash
# Convert frames first:
for f in my-frames/frame_*.png; do
    python3 png_to_sixel.py "$f" --width 120 --height 120 > "${f%.png}.six"
done

# Animate at col 10, row 3, 12fps:
./animate-overlay.sh 10 3 my-frames 12
```

## Requirements
- Python 3 with Pillow (`pip install Pillow`)
- `bc` for shell delay calculation
