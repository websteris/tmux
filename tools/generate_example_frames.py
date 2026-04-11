#!/usr/bin/env python3
"""
Generate PNG frames of a spinning arc animation suitable for use with
tmux overlay-image via animate-overlay.sh.

Canvas is transparent (RGBA). The arc rotates clockwise with a gradient
from a dim tail to a bright leading edge.
"""

import os
import math
import argparse


def lerp_color(c1, c2, t):
    """Linear interpolate between two RGBA colors. t=0 -> c1, t=1 -> c2."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))


def hex_to_rgba(hex_color, alpha=255):
    """Convert #rrggbb hex string to (r, g, b, alpha) tuple."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (r, g, b, alpha)


def draw_arc_thick(draw, bbox, start_angle, end_angle, color, width):
    """
    Draw a thick arc by layering concentric arcs across the width range.
    PIL's arc is 1px; we simulate thickness by offsetting the bbox.
    """
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    rx = (x1 - x0) / 2
    ry = (y1 - y0) / 2

    steps = width * 2  # sub-pixel steps for smoother appearance
    for step in range(steps):
        t = step / max(steps - 1, 1)
        offset = (t - 0.5) * width
        bx0 = cx - (rx - offset)
        by0 = cy - (ry - offset)
        bx1 = cx + (rx - offset)
        by1 = cy + (ry - offset)
        if bx1 <= bx0 or by1 <= by0:
            continue
        draw.arc([bx0, by0, bx1, by1], start=start_angle, end=end_angle, fill=color, width=1)


def angle_to_xy(bbox, angle_deg, radius_offset=0):
    """Convert angle (PIL convention: 0=right, clockwise) to (x,y) on arc."""
    x0, y0, x1, y1 = bbox
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    rx = (x1 - x0) / 2 + radius_offset
    ry = (y1 - y0) / 2 + radius_offset
    rad = math.radians(angle_deg)
    x = cx + rx * math.cos(rad)
    y = cy + ry * math.sin(rad)
    return x, y


def generate_frame(frame_index, num_frames, canvas_size, color_head, color_tail):
    """Generate a single frame and return the PIL Image."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        import sys
        sys.stderr.write("Error: PIL (Pillow) is required. Install with: pip install Pillow\n")
        sys.exit(1)

    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = max(4, canvas_size // 15)
    arc_width = max(4, canvas_size // 15)
    dot_radius = max(2, canvas_size // 40)
    arc_bbox = [margin, margin, canvas_size - margin, canvas_size - margin]
    arc_sweep = 270  # degrees

    # PIL arc angles: 0=right (3 o'clock), increases clockwise
    degrees_per_frame = 360 / num_frames
    rotation = frame_index * degrees_per_frame
    lead_angle = rotation
    tail_angle = rotation - arc_sweep

    # Draw arc in segments for gradient effect
    n_segments = 36
    for seg in range(n_segments):
        t_start = seg / n_segments
        t_end = (seg + 1) / n_segments

        seg_start_angle = tail_angle + t_start * arc_sweep
        seg_end_angle = tail_angle + t_end * arc_sweep

        color_start = lerp_color(color_tail, color_head, t_start)
        color_end = lerp_color(color_tail, color_head, t_end)
        color_mid = lerp_color(color_start, color_end, 0.5)

        draw_arc_thick(draw, arc_bbox, seg_start_angle, seg_end_angle, color_mid, arc_width)

    # Draw dot at the leading edge
    dot_x, dot_y = angle_to_xy(arc_bbox, lead_angle)
    draw.ellipse(
        [dot_x - dot_radius, dot_y - dot_radius, dot_x + dot_radius, dot_y + dot_radius],
        fill=color_head,
    )

    return img


def main():
    parser = argparse.ArgumentParser(
        description="Generate a spinning arc animation as PNG frames for tmux overlay-image."
    )
    parser.add_argument("--output-dir", default="./frames", help="Directory to write frame PNGs (default: ./frames)")
    parser.add_argument("--frames", type=int, default=24, help="Number of frames (default: 24)")
    parser.add_argument("--size", type=int, default=120, help="Canvas size in pixels (default: 120)")
    parser.add_argument("--color", default="#00d2d3", help="Arc head color as #rrggbb (default: #00d2d3)")
    args = parser.parse_args()

    color_head = hex_to_rgba(args.color, alpha=255)
    # Tail: same hue, reduced brightness and alpha
    r, g, b, _ = color_head
    color_tail = (max(0, r - 90), max(0, g - 90), max(0, b - 71), 180)

    os.makedirs(args.output_dir, exist_ok=True)

    for i in range(args.frames):
        img = generate_frame(i, args.frames, args.size, color_head, color_tail)
        path = os.path.join(args.output_dir, f"frame_{i:02d}.png")
        img.save(path, "PNG")
        print(f"Saved {path}")

    print(f"\nDone. {args.frames} frames written to {args.output_dir}")
    print(f"\nConvert to sixel:")
    print(f"  for f in {args.output_dir}/frame_*.png; do")
    print(f"    python3 png_to_sixel.py \"$f\" --width {args.size} --height {args.size} > \"${{f%.png}}.six\"")
    print(f"  done")
    print(f"\nThen animate:")
    print(f"  ./animate-overlay.sh X Y {args.output_dir} [FPS]")


if __name__ == "__main__":
    main()
