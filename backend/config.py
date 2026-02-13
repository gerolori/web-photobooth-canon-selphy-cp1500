import os

# --- PIN ---
PIN = "6730"

# --- Printer ---
PRINTER_NAME = "Canon SELPHY CP1500"

# --- Paths ---
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "photo")

COLLAGE_UPLOADED = os.path.join(BASE_DIR, "collage", "uploaded")
COLLAGE_PROCESSED = os.path.join(BASE_DIR, "collage", "processed")

CORRECTION_UPLOADED = os.path.join(BASE_DIR, "correction", "uploaded")
CORRECTION_PROCESSED = os.path.join(BASE_DIR, "correction", "processed")

PRINTER_QUEUE = os.path.join(BASE_DIR, "printer", "queue")
PRINTER_PRINTED = os.path.join(BASE_DIR, "printer", "printed")

PROFILES = os.path.join(BASE_DIR, "profiles")
ICC_PATH = "Canon_CP1500.icc"

# --- Photos ---
COLLAGE_W = 1847
COLLAGE_H = 1247
DPI = 300

BORDER_OUTER_MM = 6
BORDER_CENTER_MM = 4
GREEN_FACTOR = 0.97

# === Adjustable corrections for margin calibration ===
CORR_TOP_MM = -0.5
CORR_BOTTOM_MM = -0.5
CORR_LEFT_MM = 1.5
CORR_RIGHT_MM = 1


# --- Ensure folders exist ---
for path in [COLLAGE_UPLOADED, COLLAGE_PROCESSED,
             CORRECTION_UPLOADED, CORRECTION_PROCESSED,
             PRINTER_QUEUE, PRINTER_PRINTED]:
    os.makedirs(path, exist_ok=True)
