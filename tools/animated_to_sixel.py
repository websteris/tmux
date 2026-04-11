#!/usr/bin/env python3
"""
Convert an animated image (GIF, APNG, WebP) to a framed sixel stream.

Protocol (stdout, binary):
  Line 1: "SIXANIM <nframes>\n"
  Per frame:
    "SIXANIM_FRAME <duration_ms> <sixel_byte_count>\n"
    <sixel_byte_count bytes of DCS-wrapped sixel data>

Usage: animated_to_sixel.py <file> [--width PX] [--height PX]
"""

import sys
import os
import argparse

try:
    from PIL import Image, ImageSequence
except ImportError:
    sys.stderr.write("Error: PIL (Pillow) required. Install with: pip install Pillow\n")
    sys.exit(1)


def encode_rle(values):
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


def frame_to_sixel_bytes(rgba_img):
    """Convert an RGBA PIL Image to DCS-wrapped sixel bytes."""
    w, h = rgba_img.size

    rgb_img = Image.new("RGB", (w, h), (0, 0, 0))
    rgb_img.paste(rgba_img, mask=rgba_img.split()[3])
    quantized = rgb_img.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=0)

    palette_data = quantized.getpalette()
    num_colors = len(palette_data) // 3
    quant_pixels = list(quantized.tobytes())
    alpha_pixels = list(rgba_img.split()[3].tobytes())

    out = []

    # P2=1: unset pixels retain terminal content (transparent)
    header = "\033P0;1;0q\"1;1;%d;%d" % (w, h)
    out.append(header.encode("ascii"))

    for ci in range(num_colors):
        r = palette_data[ci * 3]
        g = palette_data[ci * 3 + 1]
        b = palette_data[ci * 3 + 2]
        r100 = round(r * 100 / 255)
        g100 = round(g * 100 / 255)
        b100 = round(b * 100 / 255)
        out.append(("#%d;2;%d;%d;%d" % (ci + 1, r100, g100, b100)).encode("ascii"))

    num_bands = (h + 5) // 6
    for band in range(num_bands):
        band_y = band * 6
        rows_in_band = min(6, h - band_y)
        first_color_in_band = True

        for ci in range(num_colors):
            sixel_chars = []
            has_any = False
            for x in range(w):
                bits = 0
                for row in range(rows_in_band):
                    py = band_y + row
                    pixel_idx = py * w + x
                    if alpha_pixels[pixel_idx] >= 128 and quant_pixels[pixel_idx] == ci:
                        bits |= (1 << row)
                if bits != 0:
                    has_any = True
                sixel_chars.append(chr(63 + bits))

            if not has_any:
                continue
            if not first_color_in_band:
                out.append(b"$")
            first_color_in_band = False
            out.append(("#%d" % (ci + 1)).encode("ascii"))
            out.append(encode_rle(sixel_chars))

        if band < num_bands - 1:
            out.append(b"-")

    out.append(b"\033\\")
    return b"".join(out)


def animated_to_sixel(filepath, target_w=None, target_h=None):
    img = Image.open(filepath)

    frames_out = []
    for frame in ImageSequence.Iterator(img):
        duration = frame.info.get("duration", 100)
        if duration <= 0:
            duration = 100

        rgba = frame.convert("RGBA")

        if target_w is not None or target_h is not None:
            w, h = rgba.size
            tw = target_w if target_w is not None else max(1, round(w * target_h / h))
            th = target_h if target_h is not None else max(1, round(h * target_w / w))
            rgba = rgba.resize((tw, th), Image.LANCZOS)

        sixel_bytes = frame_to_sixel_bytes(rgba)
        frames_out.append((int(duration), sixel_bytes))

    stdout = sys.stdout.buffer
    stdout.write(("SIXANIM %d\n" % len(frames_out)).encode("ascii"))
    for dur, data in frames_out:
        stdout.write(("SIXANIM_FRAME %d %d\n" % (dur, len(data))).encode("ascii"))
        stdout.write(data)
    stdout.flush()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("filepath")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    args = ap.parse_args()
    if not os.path.isfile(args.filepath):
        sys.stderr.write("Error: file not found: %s\n" % args.filepath)
        sys.exit(1)
    animated_to_sixel(args.filepath, args.width, args.height)
