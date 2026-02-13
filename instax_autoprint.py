#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatic FIFO printer for Canon SELPHY CP1500

Features:
- One print job at a time (driver-safe)
- Filesystem-based FIFO queue
- Crash / reboot recovery
- Collision-safe archival (no WinError 183)
"""

import os
import time
from PIL import Image, ImageWin
import win32print
import win32ui

# ============================================================
# === PATHS ==================================================
# ============================================================

BASE_DIR = "photo"

TO_PRINT_DIR = os.path.join(BASE_DIR, "printer", "to_print")
PRINTING_DIR = os.path.join(BASE_DIR, "printer", "printing")
PRINTED_DIR  = os.path.join(BASE_DIR, "printer", "printed")
FAILED_DIR   = os.path.join(BASE_DIR, "printer", "failed")

for d in (TO_PRINT_DIR, PRINTING_DIR, PRINTED_DIR, FAILED_DIR):
    os.makedirs(d, exist_ok=True)

# ============================================================
# === PRINTER CONFIGURATION =================================
# ============================================================

PRINTER_NAME = "Canon SELPHY CP1500"

# ============================================================
# === SAFE MOVE (NO COLLISIONS) ===============================
# ============================================================

def safe_move(src, dst_dir):
    """
    Move a file into dst_dir.
    If a file with the same name already exists,
    generate a unique name instead of failing.
    """
    base = os.path.basename(src)
    name, ext = os.path.splitext(base)

    candidate = os.path.join(dst_dir, base)
    counter = 1

    while os.path.exists(candidate):
        candidate = os.path.join(dst_dir, f"{name}__{counter}{ext}")
        counter += 1

    os.rename(src, candidate)
    return candidate

# ============================================================
# === PRINT FUNCTION ========================================
# ============================================================

def print_image(file_path):
    """
    Print a single image.
    Must be called by only one worker at a time.
    """

    print(f"[PRINT] Printing {file_path} on {PRINTER_NAME}…")

    img = Image.open(file_path).convert("RGB")

    # Auto-rotate if landscape
    if img.width > img.height:
        img = img.rotate(90, expand=True)

    bmp_path = file_path + ".bmp"
    img.save(bmp_path, "BMP")

    try:
        hprinter = win32print.OpenPrinter(PRINTER_NAME)

        printer_dc = win32ui.CreateDC()
        printer_dc.CreatePrinterDC(PRINTER_NAME)

        printer_dc.StartDoc(os.path.basename(file_path))
        printer_dc.StartPage()

        bmp = Image.open(bmp_path)
        dib = ImageWin.Dib(bmp)

        x_res = printer_dc.GetDeviceCaps(8)   # HORZRES
        y_res = printer_dc.GetDeviceCaps(10)  # VERTRES

        # Full-page draw (driver handles borderless / fill)
        dib.draw(printer_dc.GetHandleOutput(), (0, 0, x_res, y_res))

        printer_dc.EndPage()
        printer_dc.EndDoc()

        printer_dc.DeleteDC()
        win32print.ClosePrinter(hprinter)

        print("[OK] Print completed")

    finally:
        if os.path.exists(bmp_path):
            os.remove(bmp_path)

# ============================================================
# === CRASH / REBOOT RECOVERY ================================
# ============================================================

def recover_printing_files():
    """
    If the system or script crashes while printing,
    files may be left in PRINTING_DIR.
    Re-queue them on startup.
    """
    for f in os.listdir(PRINTING_DIR):
        src = os.path.join(PRINTING_DIR, f)
        dst = os.path.join(TO_PRINT_DIR, f)
        os.rename(src, dst)
        print(f"[RECOVER] Re-queued unfinished job: {f}")

# ============================================================
# === FIFO WORKER ============================================
# ============================================================

def print_worker():
    """
    Main FIFO loop.
    Uses the filesystem as a persistent queue.
    Exactly one file is allowed in PRINTING_DIR.
    """

    print("[WORKER] Printer worker started")

    while True:
        # If something is currently printing, wait
        if os.listdir(PRINTING_DIR):
            time.sleep(1)
            continue

        files = sorted(
            f for f in os.listdir(TO_PRINT_DIR)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        )

        if not files:
            time.sleep(1)
            continue

        next_file = files[0]
        src = os.path.join(TO_PRINT_DIR, next_file)
        printing_path = os.path.join(PRINTING_DIR, next_file)

        try:
            # Atomic move = lock acquisition
            os.rename(src, printing_path)
        except OSError:
            continue

        try:
            print_image(printing_path)

            final_path = safe_move(printing_path, PRINTED_DIR)
            print(f"[DONE] Archived as {os.path.basename(final_path)}")

        except Exception as e:
            print(f"[ERROR] Printing failed for {next_file}: {e}")
            safe_move(printing_path, FAILED_DIR)

# ============================================================
# === MAIN ===================================================
# ============================================================

if __name__ == "__main__":
    recover_printing_files()
    print_worker()
