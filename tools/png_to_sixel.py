#!/usr/bin/env python3
"""
Convert a PNG (with alpha) to sixel format for use with tmux overlay-image.
Transparent pixels (alpha < 128) are left unset so P2=1 background shows through.

Usage: python3 png_to_sixel.py <input.png> [--width PX] [--height PX]
Output: sixel data written to stdout (binary)
"""

import sys
import os

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("Error: PIL (Pillow) is required. Install with: pip install Pillow\n")
    sys.exit(1)


def encode_rle(values):
    """Encode a list of sixel characters using RLE for runs >= 4."""
    if not values:
        return b""
    result = []
    i = 0
    while i < len(values):
        ch = values[i]
        count = 1
        while i + count < len(values) and values[i + count] == ch:
            count += 1
        if count >= 4:
            result.append(("!%d%s" % (count, ch)).encode("ascii"))
        else:
            result.append((ch * count).encode("ascii"))
        i += count
    return b"".join(result)


def png_to_sixel(filepath, target_w=None, target_h=None):
    img = Image.open(filepath).convert("RGBA")
    w, h = img.size

    # Scale to target pixel dimensions if requested, preserving aspect ratio
    # when only one dimension is given.
    if target_w is not None or target_h is not None:
        if target_w is None:
            target_w = max(1, round(w * target_h / h))
        if target_h is None:
            target_h = max(1, round(h * target_w / w))
        img = img.resize((target_w, target_h), Image.LANCZOS)
        w, h = img.size

    # Quantize to 255 colors (register 0 reserved as background/transparent)
    # We need to quantize only the opaque pixels for best color accuracy.
    # Use PIL's quantize on a version with white matte to get palette, but
    # we track alpha separately from the original RGBA image.
    rgb_img = Image.new("RGB", (w, h), (0, 0, 0))
    rgb_img.paste(img, mask=img.split()[3])  # paste with alpha mask
    quantized = rgb_img.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=0)

    palette_data = quantized.getpalette()  # flat list: [r,g,b, r,g,b, ...]
    num_colors = len(palette_data) // 3   # actual palette entries (may be < 255)
    quant_pixels = list(quantized.tobytes())  # palette index per pixel (0..num_colors-1)
    alpha_pixels = list(img.split()[3].tobytes())  # alpha per pixel (0..255)

    # Build the output in parts
    out = []

    # DCS header: P2=1 means unspecified pixels retain current terminal content (transparent)
    # P2=0 or P2=2 would fill unset pixels with color register 0 (opaque)
    # Format: ESC P <P1>;<P2>;<P3> q "<Pan>;<Pad>;<Ph>;<Pv>
    header = "\033P0;1;0q\"1;1;%d;%d" % (w, h)
    out.append(header.encode("ascii"))

    # Emit color register definitions (1-based: register ci+1 for palette index ci)
    # Format: #<reg>;2;<r>;<g>;<b>  (mode 2 = RGB, values 0-100)
    for ci in range(num_colors):
        r = palette_data[ci * 3]
        g = palette_data[ci * 3 + 1]
        b = palette_data[ci * 3 + 2]
        r100 = round(r * 100 / 255)
        g100 = round(g * 100 / 255)
        b100 = round(b * 100 / 255)
        reg = ci + 1
        out.append(("#%d;2;%d;%d;%d" % (reg, r100, g100, b100)).encode("ascii"))

    # Render sixel bands (each band = 6 rows)
    num_bands = (h + 5) // 6

    for band in range(num_bands):
        band_y = band * 6
        # rows in this band (may be < 6 for last band)
        rows_in_band = min(6, h - band_y)

        # For each color register, build the sixel row data
        # We only emit a color if it has at least one opaque pixel in this band
        first_color_in_band = True

        for ci in range(255):
            reg = ci + 1
            # Build sixel chars for this color across all x positions
            sixel_chars = []
            has_any = False

            for x in range(w):
                bits = 0
                for row in range(rows_in_band):
                    py = band_y + row
                    px = x
                    pixel_idx = py * w + px
                    alpha = alpha_pixels[pixel_idx]
                    if alpha >= 128 and quant_pixels[pixel_idx] == ci:
                        bits |= (1 << row)
                if bits != 0:
                    has_any = True
                sixel_chars.append(chr(63 + bits))

            if not has_any:
                continue

            # Emit carriage return before second+ color in band
            if not first_color_in_band:
                out.append(b"$")
            first_color_in_band = False

            # Emit color selector
            out.append(("#%d" % reg).encode("ascii"))

            # Emit RLE-encoded sixel row
            out.append(encode_rle(sixel_chars))

        # End of band: '-' advances to next sixel band (unless last band)
        if band < num_bands - 1:
            out.append(b"-")

    # String terminator: ESC \
    out.append(b"\033\\")

    sys.stdout.buffer.write(b"".join(out))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("filepath")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    args = ap.parse_args()
    if not os.path.isfile(args.filepath):
        sys.stderr.write("Error: file not found: %s\n" % args.filepath)
        sys.exit(1)
    png_to_sixel(args.filepath, args.width, args.height)
