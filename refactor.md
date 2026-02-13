Great, we can structure the stack in a modular way like this:

* **Color-Corrector**: applies ICC and green correction to images.
* **Collage-Builder**: generates 2x2 collages as before, with border and rotation settings.
* **Printer-Service**: receives images (single or collages) via upload and sends them to the printer email (mail-to-print).
* **Frontend**: simple web UI for uploads and mode selection (single image or collage).

---

## 1. Project structure

```
photo-printer/
│
├─ docker-compose.yml
├─ color-corrector/
│   ├─ Dockerfile
│   ├─ requirements.txt
│   └─ corrector.py
├─ collage-builder/
│   ├─ Dockerfile
│   ├─ requirements.txt
│   └─ collage.py
├─ printer-service/
│   ├─ Dockerfile
│   ├─ requirements.txt
│   └─ main.py
└─ frontend/
    ├─ Dockerfile
    ├─ requirements.txt
    └─ app.py
```

---

## 2. Overall flow

1. The user uploads photos via the **frontend**.
2. The user chooses **single photo mode** or **2x2 collage**.
3. If single photo -> **Color-Corrector** -> send to **Printer-Service**.
4. If collage -> **Color-Corrector** for each photo -> **Collage-Builder** -> output -> **Printer-Service**.

Each container communicates through an internal **REST API** or a **shared folder mounted as a volume**.

---

### 3. Shared volumes

```yaml
volumes:
  uploads:
  tmp:
  collage:
```

* `uploads`: images uploaded by the user.
* `tmp`: temporary images processed by the color-corrector.
* `collage`: collage output ready for printing.

---

## 4. Base docker-compose.yml

```yaml
version: "3.9"

services:
  frontend:
    build: ./frontend
    ports:
      - "8080:8080"
    volumes:
      - uploads:/app/uploads
      - tmp:/app/tmp
    environment:
      - COLOR_CORRECTOR_URL=http://color-corrector:8000
      - COLLAGE_BUILDER_URL=http://collage-builder:8000
      - PRINTER_SERVICE_URL=http://printer-service:8001

  color-corrector:
    build: ./color-corrector
    volumes:
      - uploads:/app/uploads
      - tmp:/app/tmp
    ports:
      - "8000:8000"

  collage-builder:
    build: ./collage-builder
    volumes:
      - tmp:/app/tmp
      - collage:/app/collage
    ports:
      - "8000:8000"

  printer-service:
    build: ./printer-service
    volumes:
      - collage:/app/tmp
      - tmp:/app/tmp
    ports:
      - "8001:8001"
    environment:
      - MAIL_TO_PRINT="stampante@example.com"
      - SMTP_SERVER="smtp.example.com"
      - SMTP_PORT=587
      - SMTP_USER="user@example.com"
      - SMTP_PASS="password"

volumes:
  uploads:
  tmp:
  collage:
```

---

## 5. Frontend (`frontend/app.py`) minimal example

```python
from flask import Flask, request, render_template, redirect
import requests
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

COLOR_CORRECTOR_URL = os.environ.get("COLOR_CORRECTOR_URL", "http://color-corrector:8000")
COLLAGE_BUILDER_URL = os.environ.get("COLLAGE_BUILDER_URL", "http://collage-builder:8000")
PRINTER_SERVICE_URL = os.environ.get("PRINTER_SERVICE_URL", "http://printer-service:8001")

@app.route("/", methods=["GET"])
def index():
    return """
    <h2>Upload photos</h2>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" multiple>
        <select name="mode">
            <option value="single">Single photo</option>
            <option value="collage">Collage 2x2</option>
        </select>
          <input type="submit" value="Send">
    </form>
    """

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("file")
    mode = request.form.get("mode")

    saved_files = []
    for f in files:
        path = os.path.join(UPLOAD_FOLDER, f.filename)
        f.save(path)
        saved_files.append(path)

    if mode == "single":
        for f in saved_files:
            requests.post(f"{PRINTER_SERVICE_URL}/print", files={"file": open(f,"rb")})
    else:
        # Send to collage builder
        r = requests.post(f"{COLLAGE_BUILDER_URL}/build", files=[("files", open(f,"rb")) for f in saved_files])
        # Then send collage output to printer
        output_file = r.json()["collage"]
        with open(output_file, "rb") as f:
            requests.post(f"{PRINTER_SERVICE_URL}/print", files={"file": f})

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

---

With this structure you get:

* **Scalability**: update or replace one container without touching the others.
* **Flexibility**: single photo or collage.
* **Security**: you can expose only the frontend via Cloudflare Tunnel or HTTPS proxy, while the backend remains internal.
* **Automatic printing**: via mail-to-print, without installing drivers on the VPS.

---
