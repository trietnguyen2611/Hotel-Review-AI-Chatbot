# Desktop App

The desktop app uses Electron to run the existing web UI in a native macOS or
Windows window. React is not added because the current UI already works without
a framework; keeping it avoids a risky rewrite of the chat and hotel workflows.

## Development

1. Install Node.js 20 or newer and Python 3.10–3.12.
2. Install the Python dependencies from `requirements.txt` in the project
   environment.
3. Install the desktop dependencies with `npm install`.
4. Start the desktop app with `npm run desktop`.

The launcher uses `.venv` when present. Otherwise it uses Python 3.12
(`python3.12` on macOS or `py -3.12` on Windows). Set `HOTEL_QA_PYTHON` to use a
different interpreter.
The desktop app starts the Python server on a random loopback port and closes
it when the desktop process exits.

## Build installers

Run the target build on the matching operating system:

- macOS: `npm run desktop:dist:mac` creates a DMG and ZIP.
- Windows: `npm run desktop:dist:win` creates an NSIS installer.

Build artifacts are written to `release/`. The installers include the UI and
hotel review dataset, but do not include Python, Python dependencies, or model
weights. The model directory is several gigabytes, so it is intentionally not
copied into the installer. Install the Python requirements before launching the
installed app. Model weights can be uploaded from the app and are saved in the
per-user application data directory. For a self-contained installer, the
Python backend and selected model need to be packaged as platform-specific
assets. The generated installers are unsigned; public distribution requires
platform-specific code signing (and macOS notarization).
