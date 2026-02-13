# Canon CP1500 Photo Booth

Local photo booth app for Canon SELPHY CP1500 only. It provides a Flask web UI for uploads, builds 2x2 collages, applies color correction and ICC profiles, queues files for printing, and runs a simple local print workflow.

This repo is a refactor focused on clearer structure and centralized configuration. It still targets the CP1500 only.

## Repo structure

- backend/app.py: Flask server, upload endpoints, collage watcher, Cloudflare Tunnel launch.
- backend/collage.py: collage builder and layout rules.
- backend/color.py: ICC-based correction pipeline.
- backend/config.py: shared constants derived from config.yaml.
- backend/printer.py: local Windows printer integration.
- config.yaml: runtime configuration (paths, collage sizing, ICC, PIN).
- templates/: UI pages (collage upload, postcards, correction status).
- photo/: local storage and print queues (content ignored by git, structure kept).

## Requirements

- Python 3.10+ recommended
- Windows for printing via pywin32 (backend/printer.py)
- Canon SELPHY CP1500 driver installed (this project targets CP1500 only)
- Optional: cloudflared in PATH if you want a tunnel

## Quick start

1) Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install flask pillow pywin32 pyyaml
```

2) Review config.yaml and update the PIN, paths, and collage settings if needed.

3) Optional: add your Cloudflare hostname to .env:

```bash
CLOUDFLARE_TUNNEL_HOSTNAME=your.hostname.example
```

4) Start the app:

```bash
python backend/app.py
```

Open http://localhost:5000 in your browser.

## How it works

- Uploads go to photo/collage/uploaded.
- The watcher groups images into sets of 4, generates a collage, and queues it.
- The correction pipeline writes into photo/correction/processed.
- Printed files are moved into photo/printer/printed.

## Cloudflare Tunnel

backend/app.py will attempt to start cloudflared automatically. It passes --url http://localhost:5000 and, if set, --hostname from .env. If you do not want a tunnel, leave the env var empty and do not install cloudflared.

WARNING: Do not expose this app to the public internet. It is not security hardened and has no real authentication. If you must expose it temporarily, restrict access (for example, a geolocation allowlist in Cloudflare), and keep the exposure window as short as possible. ⚠️

## Security notes

- The upload PIN is stored in config.yaml and checked client side. Treat it as public. If you need real access control, move it server-side and remove it from the UI.
- .env is ignored by git. Do not commit secrets.

## Differences from the previous version

- Modular backend with separate collage, color correction, and printer modules.
- Centralized configuration in config.yaml instead of hardcoded values.
- New queue paths under photo/collage, photo/correction, and photo/printer.
- UI split into pages for collage, postcards, and correction status.
- Cloudflare hostname read from .env with an empty default.

## Future steps toward an ultimate CP1500 auto-print script

- Make the printing backend pluggable (Windows pywin32 and CUPS/IPP for macOS/Linux).
- Move PIN and admin controls to server-side configuration with proper auth.
- Add a dedicated print worker service with retries, backoff, and job history.
- Introduce structured logging, metrics, and a small admin dashboard.
- Support network printing to avoid USB passthrough limits in Docker.
- Add Docker images and a compose file with volumes for the queues.
- Add test fixtures for collage layout, color correction, and queue flow.