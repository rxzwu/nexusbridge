# NexusBridgeHub

[![PyPI version](https://img.shields.io/pypi/v/nexusbridgehub)](https://pypi.org/project/nexusbridgehub/)
[![Python 3.11–3.14](https://img.shields.io/badge/python-3.11--3.14-blue.svg)](https://pypi.org/project/nexusbridgehub/)
[![Tests](https://github.com/rxzwu/nexusbridgehub/actions/workflows/ci.yml/badge.svg)](https://github.com/rxzwu/nexusbridgehub/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Universal bridge for distributed bot control: **bot → server → user worker**.

Add a thin integration layer to any Python bot or automation project — keep your business logic local, control it remotely through a central server.

> **Русская документация:** [README.ru.md](README.ru.md) · **Деплой на VPS:** [docs/DEPLOY.ru.md](docs/DEPLOY.ru.md) · **Проверка:** [docs/TESTING.ru.md](docs/TESTING.ru.md)

## Python versions

| Version | Status |
|---------|--------|
| **3.10 and below** | Not supported — `pip` will refuse to install |
| **3.11 – 3.14** | Fully supported — every release is tested in CI on 3.11, 3.12, 3.13, and 3.14 |

Requires **Python 3.11+**. Check your version: `python --version`.

## Architecture

```
┌─────────────┐   JWT controller  ┌──────────────┐   JWT worker   ┌─────────────────┐
│ Telegram    │ ────────────────► │NexusBridgeHub│ ◄───────────── │ User Worker App │
│ Bot / API   │                   │   Server     │                │ (local runtime) │
└─────────────┘                   └──────────────┘                └─────────────────┘
```

| Component | Role |
|-----------|------|
| **Server** | Routes commands from bot to the correct user's worker |
| **BridgeClient** | Embedded in a project on the user's machine; executes registered functions |
| **BridgeController** | Used by a bot or API to invoke remote functions |
| **WorkerApp** | Thin standalone client; pairs via code, no secrets in binary |

## Security model

- **JWT tokens** — workers and controllers authenticate with short-lived tokens (no hardcoded secrets in the app)
- **Pair codes** — bot generates 8-char code; user enters it in the worker app → receives JWT
- **Encrypted server URL** — WSS address stored as AES-256-GCM blob with PBKDF2 key derivation + machine fingerprint (not plain text in `.exe`)
- **Thin client build** — `nexusbridgehub-build` generates per-build seed; combine with PyInstaller + optional commercial obfuscators

## Error handling and logging

- A failing **handler** does not crash the worker — the error is returned as `ok: false` and the worker keeps running
- **Auto-reconnect** on WebSocket drops (`BridgeClient`, `WorkerApp`)
- **Invalid messages** are logged and skipped; the session stays alive
- Log level: `NEXUSBRIDGEHUB_LOG_LEVEL=DEBUG` (default `INFO`)

## Install

```bash
pip install nexusbridgehub
# or from source
pip install -e ".[dev]"
```

## Quick start

### 1. Start server (VPS)

```bash
export NEXUSBRIDGEHUB_JWT_SECRET="your-48-char-minimum-secret-key-here"
nexusbridgehub-server --host 0.0.0.0 --port 8765
```

### 2. Embed in your project (user's machine)

```python
from nexusbridgehub import BridgeClient

bridge = BridgeClient(
    server_url="wss://bridge.example.com:8765",
    token=user_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
bridge.register("run_task", run_task)
bridge.register("worker_status", get_worker_status)
await bridge.run()
```

### 3. Bot side (controller on VPS)

```python
from nexusbridgehub import AuthManager, BridgeController
from nexusbridgehub.protocol import Role

auth = AuthManager(os.environ["NEXUSBRIDGEHUB_JWT_SECRET"])

# Generate pair code for user (show in Telegram)
code = auth.create_pair_code(project_id="taskrelay", user_id=str(user_id))

# After user paired — invoke remote functions
bot_jwt = auth.create_token(role=Role.CONTROLLER, project_id="taskrelay", user_id=str(user_id))
ctrl = BridgeController(
    server_url="wss://bridge.example.com:8765",
    token=bot_jwt,
    project_id="taskrelay",
    user_id=str(user_id),
)
result = await ctrl.invoke("run_task", {"job_id": "job-42"})
```

### 4. Build standalone worker binary

Build a distributable executable for users (no Python required on their machine):

```bash
# Install with builder dependencies
pip install nexusbridgehub[builder]

# Build worker binary with encrypted server URL
nexusbridgehub --server-url wss://bridge.example.com:8765

# Build with custom handlers
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --register-code handlers.py \
    --icon app.ico \
    --name myapp-worker
```

**Output:** Single-file executable in `./dist/` (Windows: `.exe`, macOS/Linux: binary)

**Features:**
- Encrypted server URL (AES-256-GCM + machine fingerprint)
- Custom command handlers embedded
- No Python installation needed
- Cross-platform: Windows, macOS, Linux

See [docs/BUILD.md](docs/BUILD.md) for details and [docs/CI-CD.md](docs/CI-CD.md) for automated multi-platform builds.

## Per-user workers

Each end user runs a worker app on their own machine:

1. User opens the bot → bot shows a **pair code**
2. User runs the worker with that code → worker connects to your bridge server
3. Bot sends `run_task`, `worker_status`, etc. → commands execute on **the user's machine**
4. Local resources stay on the user's device — the bot only orchestrates

See [`examples/minimal/`](examples/minimal/) for a step-by-step RU/EN worker test, [`examples/worker_integration.py`](examples/worker_integration.py) (EN) or [`examples/worker_integration.ru.py`](examples/worker_integration.ru.py) (RU) for project integration stubs.

## Protocol

JSON messages over WebSocket:

| Type | Direction | Purpose |
|------|-----------|---------|
| `register` | client → server | Join as worker or controller |
| `invoke` | controller → worker | Call registered function |
| `result` | worker → controller | Return value or error |
| `pair_request` | worker → server | Redeem pair code for JWT |

## Deployment

Production guide (VPS, systemd, WSS, Hetzner/Contabo): [docs/DEPLOY.ru.md](docs/DEPLOY.ru.md)

## Development

```bash
pip install -e ".[dev]"
pytest
python -m build   # PyPI wheel
python -m twine check dist/*
```

Release guide: [docs/PUBLISH.ru.md](docs/PUBLISH.ru.md)

## License

MIT
