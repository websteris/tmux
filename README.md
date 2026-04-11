# tmux transparent animated sixel overlay

Adds `overlay-image` to tmux: render a transparent PNG or sixel image at
absolute screen coordinates, outside any pane, with live terminal content
showing through transparent areas.

## What it does

```
tmux overlay-image set X Y FILE [-W cols] [-H rows]
tmux overlay-image animate X Y FILE [-W cols] [-H rows]
tmux overlay-image clear
```

- **X Y** — cell coordinates (column, row) on the terminal screen
- **FILE** — `.png`/`.six` for `set`; animated `.gif`/`.webp`/`.apng` for `animate`
- **-W / -H** — scale to N terminal columns / rows
- **Transparent** — alpha < 128 shows live terminal content through (P2=1)
- **Per-frame durations** — extracted from the animation file metadata automatically
- **Flicker-free** — redraws within every pane sync block

## Apply to tmux

```bash
# Clone tmux (next branch recommended)
git clone https://github.com/tmux/tmux.git
cd tmux

# Apply the patch
git am /path/to/patches/0001-feat-transparent-animated-sixel-image-overlay-system.patch

# Build
sh autogen.sh && ./configure && make
sudo make install
```

Requires tmux built with `--enable-sixel` (needs libsixel or built-in sixel support).
Also requires `terminal-features '*:sync'` in `~/.tmux.conf` for flicker-free rendering.

## Tools

See [`tools/README.md`](tools/README.md) for:
- `png_to_sixel.py` — convert PNG with alpha to sixel
- `generate_example_frames.py` — generate a spinning arc animation
- `animate-overlay.sh` — loop through `.six` frames at a given fps

## Requirements

- tmux built from source with sixel support (`--enable-sixel`)
- giflib 5.x (`brew install giflib` or `apt install libgif-dev`) for `animate`
- libpng (`brew install libpng` or `apt install libpng-dev`) for `set` with `.png`
- A terminal with sixel support (Windows Terminal, WezTerm, xterm, mlterm, etc.)
- `set -ga terminal-features '*:sync'` in `~/.tmux.conf`
