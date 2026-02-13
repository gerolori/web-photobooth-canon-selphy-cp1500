#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import uuid
import threading
import subprocess
import platform
import shutil

from flask import Flask, request, redirect, render_template, jsonify
from werkzeug.utils import secure_filename
from PIL import Image, ImageCms

from instax_collage import build_collage

# ============================================================
# === ENV (OPTIONAL .env LOAD) ===============================
# ============================================================

def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_dotenv()

# ============================================================
# === PATHS ==================================================
# ============================================================

BASE_DIR = "photo"

UPLOAD_COLLAGE   = os.path.join(BASE_DIR, "upload", "collage")
UPLOAD_POSTCARD  = os.path.join(BASE_DIR, "upload", "postcard")

PROCESSING_POSTCARD = os.path.join(BASE_DIR, "processing", "postcard")

PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

PRINTER_DIR       = os.path.join(BASE_DIR, "printer")
PRINTER_TO_PRINT  = os.path.join(PRINTER_DIR, "to_print")
PRINTER_PRINTED   = os.path.join(PRINTER_DIR, "printed")

for d in [
    UPLOAD_COLLAGE,
    UPLOAD_POSTCARD,
    PROCESSING_POSTCARD,
    PROCESSED_DIR,
    PRINTER_TO_PRINT,
    PRINTER_PRINTED,
]:
    os.makedirs(d, exist_ok=True)

# ============================================================
# === CONFIG =================================================
# ============================================================

app = Flask(__name__, template_folder="templates", static_folder="static")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PIN = "6730"

CLOUDFLARE_TUNNEL_HOSTNAME = os.environ.get("CLOUDFLARE_TUNNEL_HOSTNAME", "")

ICC_PROFILE = "Canon_CP1500.icc"
GREEN_FACTOR = 0.97


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def unique_name(original_name: str) -> str:
    """
    Generate a globally unique filename while preserving extension.
    This guarantees zero collisions in printer queues.
    """
    base, ext = os.path.splitext(secure_filename(original_name))
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{base}{ext}"


# ============================================================
# === FILE STABILITY CHECK ==================================
# ============================================================

def wait_for_complete_file(path, timeout=5):
    """
    Wait until a file stops growing.
    Prevents reading partially written uploads.
    """
    last_size = -1
    start = time.time()

    while time.time() - start < timeout:
        try:
            size = os.path.getsize(path)
        except OSError:
            return False

        if size == last_size:
            return True

        last_size = size
        time.sleep(0.2)

    return False


# ============================================================
# === COLOR CORRECTION ======================================
# ============================================================

def apply_green_correction(image: Image.Image) -> Image.Image:
    r, g, b = image.split()
    g = g.point(lambda i: int(i * GREEN_FACTOR))
    return Image.merge("RGB", (r, g, b))


def apply_icc_inplace(img: Image.Image) -> Image.Image:
    if not os.path.exists(ICC_PROFILE):
        return img

    try:
        srgb = ImageCms.createProfile("sRGB")
        printer = ImageCms.getOpenProfile(ICC_PROFILE)
        transform = ImageCms.buildTransform(srgb, printer, "RGB", "RGB")
        return ImageCms.applyTransform(img, transform)
    except Exception as e:
        print(f"[ICC] Failed ICC transform: {e}")
        return img


# ============================================================
# === COLLAGE WATCHER =======================================
# ============================================================

def watcher_collage_loop():
    print("[WATCHER] Collage watcher started")

    while True:
        files = sorted(
            [
                os.path.join(UPLOAD_COLLAGE, f)
                for f in os.listdir(UPLOAD_COLLAGE)
                if allowed_file(f)
            ],
            key=os.path.getmtime,
        )

        if len(files) >= 4:
            selected = files[:4]
            collage_name = unique_name("collage.jpg")
            collage_path = os.path.join(PROCESSED_DIR, collage_name)

            try:
                build_collage(selected, collage_path)

                img = Image.open(collage_path).convert("RGB")
                img = apply_green_correction(img)
                img = apply_icc_inplace(img)
                img.save(collage_path)

                shutil.copy2(collage_path, os.path.join(PRINTER_TO_PRINT, collage_name))

                for f in selected:
                    shutil.move(f, PROCESSED_DIR)

                print(f"[COLLAGE] Created and queued {collage_name}")

            except Exception as e:
                print(f"[COLLAGE] Batch error: {e}")

        time.sleep(2)


# ============================================================
# === POSTCARD WATCHER (FIFO SAFE) ===========================
# ============================================================

def watcher_postcard_loop():
    print("[WATCHER] Postcard watcher started")

    while True:
        files = [
            os.path.join(UPLOAD_POSTCARD, f)
            for f in os.listdir(UPLOAD_POSTCARD)
            if allowed_file(f)
        ]

        for src in files:
            try:
                if not wait_for_complete_file(src):
                    continue

                unique = unique_name(os.path.basename(src))
                processing_path = os.path.join(PROCESSING_POSTCARD, unique)

                # Atomic move = lock
                os.rename(src, processing_path)

                img = Image.open(processing_path).convert("RGB")
                img = apply_green_correction(img)
                img = apply_icc_inplace(img)

                processed_copy = os.path.join(PROCESSED_DIR, unique)
                printer_target = os.path.join(PRINTER_TO_PRINT, unique)

                img.save(processed_copy)
                img.save(printer_target)

                os.remove(processing_path)

                print(f"[POSTCARD] Processed and queued {unique}")

            except Exception as e:
                print(f"[POSTCARD] Error processing {src}: {e}")

        time.sleep(2)


# ============================================================
# === ROUTES =================================================
# ============================================================

@app.route("/")
def index():
    return render_template("index.html", **get_counters())


@app.route("/counters")
def counters():
    return jsonify(get_counters())


def get_counters():
    collage_files = [f for f in os.listdir(UPLOAD_COLLAGE) if allowed_file(f)]
    num_pending = len(collage_files)

    upload_count = 4 - (num_pending % 4) if num_pending else 4
    if upload_count == 4 and num_pending >= 4:
        upload_count = 0

    processed_count = len([f for f in os.listdir(PRINTER_TO_PRINT) if allowed_file(f)])

    printed_files = [f for f in os.listdir(PRINTER_PRINTED) if allowed_file(f)]
    printed_count = 0
    for f in printed_files:
        printed_count += 4 if f.startswith("collage_") else 1

    return {
        "upload_count": upload_count,
        "processed_count": processed_count,
        "printed_count": printed_count,
    }


@app.route("/postcard")
def postcard():
    return render_template("postcard.html", **get_counters())


@app.route("/upload_collage", methods=["POST"])
def upload_collage():
    files = request.files.getlist("photo")
    for file in files:
        if file and allowed_file(file.filename):
            name = unique_name(file.filename)
            file.save(os.path.join(UPLOAD_COLLAGE, name))
            print(f"[UPLOAD COLLAGE] {name}")
    return redirect("/")


@app.route("/upload_postcard", methods=["POST"])
def upload_postcard():
    if request.form.get("pin") != PIN:
        return jsonify({"error": "Invalid PIN"}), 403

    files = request.files.getlist("photo")
    for file in files:
        if file and allowed_file(file.filename):
            name = unique_name(file.filename)
            file.save(os.path.join(UPLOAD_POSTCARD, name))
            print(f"[UPLOAD POSTCARD] {name}")

    return jsonify({"status": "ok"})


# ============================================================
# === STARTUP ===============================================
# ============================================================

if __name__ == "__main__":
    threading.Thread(target=watcher_collage_loop, daemon=True).start()
    threading.Thread(target=watcher_postcard_loop, daemon=True).start()

    def run_flask():
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

    threading.Thread(target=run_flask, daemon=True).start()

    try:
        print("[INFO] Starting Cloudflared tunnel...")
        cmd = [
            "cloudflared.exe" if platform.system().lower().startswith("win") else "cloudflared",
            "tunnel",
            "--url",
            "http://localhost:5000",
        ]
        if CLOUDFLARE_TUNNEL_HOSTNAME:
            cmd.extend(["--hostname", CLOUDFLARE_TUNNEL_HOSTNAME])
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[CLOUDFLARE] Tunnel active")
    except Exception as e:
        print(f"[ERROR] Cloudflared: {e}")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("[INFO] Shutting down...")
