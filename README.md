# Instax/Canon CP1500 Photo Booth

Local photo booth app for Canon SELPHY CP1500. It provides a small Flask web UI for uploading photos, builds 2x2 collages, applies a color tweak and ICC profile, queues files for printing, and runs a FIFO print worker.

## What is in this repo

- app.py: Flask server, upload endpoints, collage/postcard processing, Cloudflare Tunnel launch.
- instax_collage.py: collage builder and image sizing rules.
- instax_autoprint.py: FIFO print worker for Windows (win32print).
- templates/: UI for collage and postcard uploads.
- photo/: local storage and print queues (content ignored by git, structure kept).
- Canon_CP1500.icc: optional ICC profile for color correction.

## Requirements

- Python 3.10+ recommended
- Windows for printing via win32print (instax_autoprint.py)
- Canon SELPHY CP1500 driver installed
- Optional: cloudflared in PATH if you want a tunnel

## Quick start

1) Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install flask pillow pywin32
```

2) Add your Cloudflare hostname to .env:

```bash
CLOUDFLARE_TUNNEL_HOSTNAME=your.hostname.example
```

3) Start the web app:

```bash
python app.py
```

4) In a second terminal, start the printer worker:

```bash
python instax_autoprint.py
```

Open http://localhost:5000 in your browser.

## How it works

- The web app writes uploads into photo/upload/*.
- Collage mode waits for 4 photos, builds a 2x2 collage, then queues the output.
- Postcard mode processes each upload immediately and queues it.
- The print worker consumes photo/printer/to_print in FIFO order.

## Cloudflare Tunnel

app.py will attempt to start cloudflared automatically. It passes --url http://localhost:5000 and, if set, --hostname from .env. If you do not want a tunnel, leave the env var empty and do not install cloudflared.

## Security notes

- The upload PIN is hardcoded in app.py and in the client-side templates. Treat it as public. If you need a real access control, move it to server-side env config and remove it from the UI. ⚠️
- .env is ignored by git. Do not commit secrets.

## Photo storage

The photo folder structure is tracked, but all files inside are ignored. The .gitkeep files preserve the directory layout for new clones.

## Common tasks

- Rebuild the collage sizing rules: edit instax_collage.py
- Adjust green correction or ICC profile: edit app.py
- Change printer name: edit instax_autoprint.py (PRINTER_NAME)

## Troubleshooting

- If cloudflared is missing, the app will still run but tunnel startup will fail.
- If prints do not start, confirm the printer name matches your Windows printer.
- If images look off, verify Canon_CP1500.icc exists and is readable.

## Future changes: 

I'd like this to be system independent (so support for both mac and linux).

I want also to explore dockerization of this but one challange is that USB passthrough is impossible with Docker, so print over IP is probably the only way, so this probably needs a small client side program to bridge between a host and that.