#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instax_collage_auto.py
2x2 collage for Canon Selphy (10x14.8 cm nominal)
- Fixed resolution 1847x1247 px
- Outer border 2mm, center border 4mm
- Auto-rotate landscape photos
- Adjustable offsets for calibration (top, bottom, left, right)
"""

import os
import argparse
from config import *
from PIL import Image, ImageCms

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_LANCZOS = Image.LANCZOS

def mm_to_px(mm):
    return int(round((mm / 25.4) * DPI))

def build_collage(imgs, output_path):
    # Convert borders and corrections to pixels
    outer_px = mm_to_px(BORDER_OUTER_MM)
    center_px = mm_to_px(BORDER_CENTER_MM)
    corr_top = mm_to_px(CORR_TOP_MM)
    corr_bottom = mm_to_px(CORR_BOTTOM_MM)
    corr_left = mm_to_px(CORR_LEFT_MM)
    corr_right = mm_to_px(CORR_RIGHT_MM)

    # Usable size
    usable_w = COLLAGE_W - 2 * outer_px - center_px - corr_left - corr_right
    usable_h = COLLAGE_H - 2 * outer_px - center_px - corr_top - corr_bottom

    cell_w = usable_w // 2
    cell_h = usable_h // 2

    positions = [
        (outer_px + corr_left, outer_px + corr_top),  # TL
        (outer_px + cell_w + center_px + corr_left, outer_px + corr_top),  # TR
        (outer_px + corr_left, outer_px + cell_h + center_px + corr_top),  # BL
        (outer_px + cell_w + center_px + corr_left, outer_px + cell_h + center_px + corr_top),  # BR
    ]

    collage = Image.new("RGB", (COLLAGE_W, COLLAGE_H), "white")

    for idx, path in enumerate(imgs):
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        im = Image.open(path).convert("RGB")

        w, h = im.size

        # Rotate landscape
        if w < h:
            im = im.rotate(90, expand=True)
            w, h = im.size

        # --- Center-fit in the cell while keeping aspect ratio ---
        ratio = w / h
        target_ratio = cell_w / cell_h

        if ratio > target_ratio:
            # wider image -> full height
            new_h = cell_h
            new_w = int(ratio * new_h)
        else:
            # taller image -> full width
            new_w = cell_w
            new_h = int(new_w / ratio)

        resized = im.resize((new_w, new_h), RESAMPLE_LANCZOS)

        # Center crop
        left = (new_w - cell_w) // 2
        top = (new_h - cell_h) // 2
        cropped = resized.crop((left, top, left + cell_w, top + cell_h))

        # Paste into collage
        collage.paste(cropped, positions[idx])

    collage.save(output_path, "JPEG", quality=100, dpi=(DPI, DPI))
    print(f"Collage saved as {output_path} ({COLLAGE_W}x{COLLAGE_H} px)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="collage_calibrated.jpg", help="Output file")
    args = parser.parse_args()

    imgs = [f"photos/{i}.jpg" for i in range(1, 5)]
    build_collage(imgs, args.out)
