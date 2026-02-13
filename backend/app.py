#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, uuid, yaml, threading, platform, subprocess
from flask import Flask, request, render_template, jsonify, redirect
from werkzeug.utils import secure_filename
from PIL import Image
from collage import build_collage  # assumed to exist

# === ENV (OPTIONAL .env LOAD) ===============================
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

# === CONFIG ===
CONFIG_PATH = "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

PIN = str(cfg["pin"])
PRINTER_NAME = cfg["printer_name"]
COLLAGE_UPLOADED = cfg["paths"]["collage_uploaded"]
COLLAGE_PROCESSED = cfg["paths"]["collage_processed"]
CORRECTION_UPLOADED = cfg["paths"]["correction_uploaded"]
CORRECTION_PROCESSED = cfg["paths"]["correction_processed"]
PRINTER_QUEUE = cfg["paths"]["printer_queue"]
PRINTER_PRINTED = cfg["paths"]["printer_printed"]
CLOUDFLARE_TUNNEL_HOSTNAME = os.environ.get(
    "CLOUDFLARE_TUNNEL_HOSTNAME",
    cfg.get("cloudflare_hostname", ""),
)

for p in [COLLAGE_UPLOADED, COLLAGE_PROCESSED,
          CORRECTION_UPLOADED, CORRECTION_PROCESSED,
          PRINTER_QUEUE, PRINTER_PRINTED]:
    os.makedirs(p, exist_ok=True)

# === APP ===
app = Flask(__name__, template_folder="templates", static_folder="static")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


# --- Thread: collage watcher ---
def generate_collage(selected):
    collage_name = f"collage_{int(time.time())}.jpg"
    collage_path = os.path.join(PRINTER_QUEUE, collage_name)
    try:
        build_collage(selected, collage_path)
        for f in selected:
            os.rename(f, os.path.join(COLLAGE_PROCESSED, os.path.basename(f)))
        print(f"[WATCHER] Collage generated: {collage_path}")
    except Exception as e:
        print(f"[WATCHER] Collage generation error: {e}")


def watcher_loop():
    print("[WATCHER] Watcher started...")
    while True:
        all_files = sorted(
            [os.path.join(COLLAGE_UPLOADED, f)
             for f in os.listdir(COLLAGE_UPLOADED)
             if allowed_file(f)],
            key=os.path.getmtime
        )
        while len(all_files) >= 4:
            selected = all_files[:4]
            threading.Thread(target=generate_collage, args=(selected,), daemon=True).start()
            all_files = all_files[4:]
        time.sleep(2)


@app.route("/")
def index():
    upload_count = len([f for f in os.listdir(COLLAGE_UPLOADED) if allowed_file(f)])
    to_print_count = len([f for f in os.listdir(PRINTER_QUEUE) if allowed_file(f)])
    printed_count = len([f for f in os.listdir(PRINTER_PRINTED) if allowed_file(f)])
    photos_printed = printed_count * 4

    return render_template("index.html",
                           upload_count=upload_count,
                           to_print_count=to_print_count,
                           photos_printed=photos_printed)


@app.route("/counters")
def counters():
    upload_count = len([f for f in os.listdir(COLLAGE_UPLOADED) if allowed_file(f)])
    to_print_count = len([f for f in os.listdir(PRINTER_QUEUE) if allowed_file(f)])
    printed_count = len([f for f in os.listdir(PRINTER_PRINTED) if allowed_file(f)])
    photos_printed = printed_count * 4

    return jsonify({
        "upload_count": upload_count,
        "to_print_count": to_print_count,
        "printed_count": printed_count,
        "photos_printed": photos_printed
    })


@app.route("/upload", methods=["POST"])
def upload_file():
    if "photo" not in request.files:
        return "No file provided", 400

    files = request.files.getlist("photo")
    for file in files:
        if not allowed_file(file.filename):
            continue

        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_name = f"{int(time.time())}_{uuid.uuid4().hex[:6]}_{name}{ext}"
        out_path = os.path.join(COLLAGE_UPLOADED, unique_name)

        try:
            img = Image.open(file.stream)
            img.thumbnail((800, 800))
            img.save(out_path, quality=85)
            print(f"[UPLOAD] {unique_name}")
        except Exception as e:
            print(f"[UPLOAD] {filename}: {e}")

    return redirect("/")


if __name__ == "__main__":
    threading.Thread(target=watcher_loop, daemon=True).start()

    def run_flask():
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

    threading.Thread(target=run_flask, daemon=True).start()

    try:
        print("\n[INFO] Starting Cloudflared tunnel...\n")
        cmd = [
            "cloudflared.exe" if platform.system().lower().startswith("win") else "cloudflared",
            "tunnel",
            "--url",
            "http://localhost:5000",
        ]
        if CLOUDFLARE_TUNNEL_HOSTNAME:
            cmd.extend(["--hostname", CLOUDFLARE_TUNNEL_HOSTNAME])

        if platform.system().lower().startswith("win"):
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        print("[CLOUDFLARE] Tunnel active\n")
    except Exception as e:
        print(f"[CLOUDFLARE] {e}")

    while True:
        time.sleep(10)
