# Desktop App

The desktop app uses Electron to run the web UI in a native macOS or
Windows window. The entire application (Electron launcher, Python backend server,
and web UI) is self-contained inside the `desktop/` directory.

## Development

1. Install Node.js 20 or newer and Python 3.10–3.12.
2. Install the Python dependencies from `requirements.txt` in the project
   environment (`pip install -r requirements.txt`).
3. Install the desktop dependencies:
   ```bash
   cd desktop
   npm install
   ```
4. Start the desktop app:
   ```bash
   # From the desktop directory:
   npm start
   # Or from the project root:
   npm --prefix desktop run desktop
   ```

The launcher uses `.venv` when present. Otherwise it uses Python 3.12
(`python3.12` on macOS or `py -3.12` on Windows). Set `HOTEL_QA_PYTHON` to use a
different interpreter.
The desktop app starts the Python server on a random loopback port and closes
it when the desktop process exits.

## Build installers

Run the target build on the matching operating system:

- macOS:
  ```bash
  cd desktop && npm run dist:mac
  # Or from project root:
  npm --prefix desktop run dist:mac
  ```
  Creates a DMG and ZIP.

- Windows:
  ```bash
  cd desktop && npm run dist:win
  # Or from project root:
  npm --prefix desktop run dist:win
  ```
  Creates an NSIS installer.

Build artifacts are written to `release/` at the project root. The installers
include the UI, launcher, and hotel review dataset, but do not include Python,
Python dependencies, or model weights. The model directory is several gigabytes,
so it is intentionally not copied into the installer. Install the Python
requirements before launching the installed app. Model weights can be uploaded
from the app and are saved in the per-user application data directory.
