# Tool Manager

A Python Flask mini-app for creative utilities including QR generation, background removal, and color extraction.

## Setup

```powershell
cd "C:\Users\Ronin David Perez\VSC PROJECTS\Tools"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the app

```powershell
cd "C:\Users\Ronin David Perez\VSC PROJECTS\Tools"
.\.venv\Scripts\Activate.ps1
python run.py
```

Then open:

http://127.0.0.1:5000

## Deploy online with Render

1. Push this project to the GitHub repository connected to Render.
2. In Render, choose **New +** -> **Blueprint** and select the repository.
3. Render will use `render.yaml` to install dependencies and start the app.
4. In the service's environment settings, set `SECRET_KEY` to a long random value.

Render will provide a public `onrender.com` URL that you can share. The free web service may sleep after inactivity, so the first request after a quiet period can take a little longer.

## Features planned

- QR code generator
- Background remover
- Color EXTRACTOR from image
- More tools later
