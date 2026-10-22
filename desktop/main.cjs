const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');

let backendProcess = null;
let mainWindow = null;
let desktopUrl = null;
let stopping = false;

function projectRoot() {
    return app.isPackaged
        ? path.join(process.resourcesPath, 'project')
        : path.join(__dirname, '..');
}

function pythonCommand(root) {
    if (process.env.HOTEL_QA_PYTHON) {
        return { command: process.env.HOTEL_QA_PYTHON, args: [] };
    }

    const venvPython = process.platform === 'win32'
        ? path.join(root, '.venv', 'Scripts', 'python.exe')
        : path.join(root, '.venv', 'bin', 'python');
    if (fs.existsSync(venvPython)) {
        return { command: venvPython, args: [] };
    }

    if (process.platform === 'win32') {
        return { command: 'py', args: ['-3.12'] };
    }
    return { command: 'python3.12', args: [] };
}

function getAvailablePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.once('error', reject);
        server.listen(0, '127.0.0.1', () => {
            const address = server.address();
            if (!address || typeof address === 'string') {
                server.close();
                reject(new Error('Could not reserve a local port for the backend.'));
                return;
            }
            const { port } = address;
            server.close((error) => error ? reject(error) : resolve(port));
        });
    });
}

function waitForBackendReady(child) {
    return new Promise((resolve, reject) => {
        let output = '';
        const timeout = setTimeout(() => {
            reject(new Error(`Backend did not start in time.\n${output.slice(-4000)}`));
        }, 5 * 60 * 1000);

        const finish = (error, url) => {
            clearTimeout(timeout);
            child.removeListener('error', onError);
            child.removeListener('exit', onExit);
            error ? reject(error) : resolve(url);
        };

        const onError = (error) => finish(error);
        const onExit = (code, signal) => {
            finish(new Error(`Backend stopped before it was ready (code ${code ?? 'unknown'}, signal ${signal ?? 'none'}).\n${output.slice(-4000)}`));
        };

        child.on('error', onError);
        child.on('exit', onExit);
        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');
        child.stdout.on('data', (chunk) => {
            output += chunk;
            const readyMatch = output.match(/HOTEL_QA_SERVER_READY=(http:\/\/127\.0\.0\.1:\d+)/);
            if (readyMatch) finish(null, readyMatch[1]);
        });
        child.stderr.on('data', (chunk) => {
            output += chunk;
        });
    });
}

async function startBackend() {
    const root = projectRoot();
    const port = await getAvailablePort();
    const python = pythonCommand(root);
    const scriptPath = fs.existsSync(path.join(__dirname, 'app.py'))
        ? path.join(__dirname, 'app.py')
        : path.join(root, 'desktop', 'app.py');

    if (!fs.existsSync(scriptPath)) {
        throw new Error(`Backend entry point not found: ${scriptPath}`);
    }

    backendProcess = spawn(python.command, [
        ...python.args,
        scriptPath,
        '--host',
        '127.0.0.1',
        '--port',
        String(port)
    ], {
        cwd: root,
        env: {
            ...process.env,
            HOTEL_QA_USER_DATA_DIR: app.getPath('userData')
        },
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe']
    });

    backendProcess.stdout.on('data', (chunk) => {
        if (process.env.ELECTRON_DEBUG) process.stdout.write(`[backend] ${chunk}`);
    });
    backendProcess.stderr.on('data', (chunk) => {
        if (process.env.ELECTRON_DEBUG) process.stderr.write(`[backend] ${chunk}`);
    });

    return waitForBackendReady(backendProcess);
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1440,
        height: 920,
        minWidth: 900,
        minHeight: 640,
        title: 'Starting Hotel Aspect AI',
        backgroundColor: '#f8f9fa',
        show: false,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true
        }
    });

    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        if (url.startsWith('https://') || url.startsWith('http://')) {
            shell.openExternal(url);
        }
        return { action: 'deny' };
    });

    mainWindow.webContents.on('will-navigate', (event, url) => {
        if (desktopUrl && new URL(url).origin !== new URL(desktopUrl).origin) event.preventDefault();
    });

    mainWindow.once('ready-to-show', () => mainWindow.show());
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
    mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`
        <!doctype html>
        <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Starting Hotel Aspect AI</title>
                <style>
                    body {
                        align-items: center;
                        background: #f8f9fa;
                        color: #202020;
                        display: flex;
                        font-family: "Segoe UI", sans-serif;
                        height: 100vh;
                        justify-content: center;
                        margin: 0;
                    }
                    main { text-align: center; }
                    p { color: #646464; }
                    .spinner {
                        animation: spin 1s linear infinite;
                        border: 3px solid #ded7f8;
                        border-top-color: #7612fa;
                        border-radius: 50%;
                        height: 28px;
                        margin: 24px auto;
                        width: 28px;
                    }
                    @keyframes spin { to { transform: rotate(360deg); } }
                </style>
            </head>
            <body>
                <main>
                    <h1>Hotel Aspect AI</h1>
                    <div class="spinner" aria-hidden="true"></div>
                    <p>Starting the local AI service. This may take a few minutes.</p>
                </main>
            </body>
        </html>
    `)}`);
}

app.whenReady().then(async () => {
    createMainWindow();
    try {
        desktopUrl = await startBackend();
        backendProcess.on('exit', (code, signal) => {
            if (stopping || !mainWindow) return;
            dialog.showMessageBox(mainWindow, {
                type: 'error',
                title: 'Hotel Aspect AI backend stopped',
                message: 'The local Python backend exited unexpectedly.',
                detail: `Exit code: ${code ?? 'unknown'}\nSignal: ${signal ?? 'none'}`
            }).finally(() => app.quit());
        });
        if (!mainWindow) createMainWindow();
        mainWindow.setTitle('Hotel Aspect AI');
        mainWindow.loadURL(desktopUrl);
    } catch (error) {
        if (stopping) return;
        await dialog.showMessageBox({
            type: 'error',
            title: 'Hotel Aspect AI could not start',
            message: 'The local Python backend could not be started.',
            detail: `${error.message}\n\nInstall the project Python requirements or set HOTEL_QA_PYTHON to a valid Python executable.`
        });
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
        if (desktopUrl) {
            mainWindow.setTitle('Hotel Aspect AI');
            mainWindow.loadURL(desktopUrl);
        }
    }
});

app.on('before-quit', () => {
    stopping = true;
    if (backendProcess && !backendProcess.killed) {
        backendProcess.kill();
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
