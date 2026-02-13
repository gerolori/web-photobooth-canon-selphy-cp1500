Perfetto, possiamo strutturare lo stack in modo modulare, così:

* **Color-Corrector**: applica ICC e correzione verde sulle immagini.
* **Collage-Builder**: genera collage 2x2 come già avevi, con impostazioni di bordo e rotazione.
* **Printer-Service**: riceve immagini (singole o collage) via upload e le invia alla mail della stampante (mail-to-print).
* **Frontend**: semplice interfaccia web per upload e scelta modalità (singola immagine o collage).

---

## 1️⃣ Struttura progetto

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

## 2️⃣ Funzionamento generale

1. L’utente carica foto tramite **frontend**.
2. L’utente sceglie **modalità singola foto** o **collage 2x2**.
3. Se singola foto → **Color-Corrector** → invio a **Printer-Service**.
4. Se collage → **Color-Corrector** per ogni foto → **Collage-Builder** → output → **Printer-Service**.

Ogni container comunica tramite **REST API** interna o **cartella condivisa montata come volume**.

---

### 3️⃣ Volumi condivisi

```yaml
volumes:
  uploads:
  tmp:
  collage:
```

* `uploads`: immagini caricate dall’utente.
* `tmp`: immagini temporanee processate dal color-corrector.
* `collage`: output collage pronto per stampa.

---

## 4️⃣ docker-compose.yml base

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

## 5️⃣ Frontend (`frontend/app.py`) esempio minimale

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
    <h2>Upload foto</h2>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" multiple>
        <select name="mode">
            <option value="single">Singola foto</option>
            <option value="collage">Collage 2x2</option>
        </select>
        <input type="submit" value="Invia">
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
        # Invia a collage builder
        r = requests.post(f"{COLLAGE_BUILDER_URL}/build", files=[("files", open(f,"rb")) for f in saved_files])
        # Poi invia output collage a printer
        output_file = r.json()["collage"]
        with open(output_file, "rb") as f:
            requests.post(f"{PRINTER_SERVICE_URL}/print", files={"file": f})

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

---

Con questa struttura hai:

* **Scalabilità**: puoi aggiornare o sostituire un container senza toccare gli altri.
* **Flessibilità**: singola foto o collage.
* **Sicurezza**: puoi esporre solo frontend tramite Cloudflare Tunnel o proxy HTTPS, mentre backend resta interno.
* **Stampa automatica**: tramite mail-to-print, senza installare driver sul VPS.

---

Se vuoi, posso scrivere **la versione completa del collage-builder** con gestione ICC integrata, margini configurabili e rotazione automatica, pronta da mettere in questo stack. Vuoi che faccia anche quello?
