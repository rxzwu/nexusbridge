# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2026-06-12

### Added

- **Pair Code Authentication** - Required for both GUI and CLI
  - Interactive pair code input in GUI (text entry field)
  - Interactive pair code prompt in CLI (keyboard input)
  - Default pair code TTL: 10 minutes (configurable via AuthManager)
  - No more hardcoded tokens - users must authenticate via bot
- **Enhanced CLI Worker**
  - Connection status display at startup
  - Interactive pair code prompt with instructions
  - `--no-prompt` flag to disable interactive input
  - Better error messages and status indicators
- **GUI Customization System**
  - Customizable colors (primary, success, error, warning)
  - Customizable fonts (family and sizes)
  - Customizable window title and dimensions
  - `--gui-config` flag to load JSON configuration
  - `GUIConfig` class with defaults
  - Example config: `examples/gui_config.json`
- **AuthManager improvements**
  - Configurable pair code TTL (default: 600 seconds = 10 minutes)
  - Better documentation of `create_pair_code` parameters

### Changed

- GUI now requires pair code on connect (no auto-connect)
- CLI prompts for pair code if not provided via arguments
- Builder accepts `--gui-config` for GUI customization
- Pair code default TTL increased from 5 to 10 minutes

## [0.2.2] - 2026-06-12

### Added

- **GUI Worker Application** (`worker_gui.py`)
  - Visual connection status indicator (connected/disconnected)
  - Real-time activity log viewer (transparency mode)
  - Connection information display (server, project, user)
  - Start/Stop controls
  - All server actions logged for user transparency
  - No secrets exposed in logs
- **Windows Version Info** for executables
  - Company name, product name, version information
  - Legal copyright and description
  - Reduces antivirus false positives
- **--gui flag** for building GUI version
  - `nexusbridgehub --server-url wss://... --gui`
  - Automatically enables --noconsole
  - Recommended for end users

### Fixed

- Antivirus false positive detection (dropper) - added Windows version metadata
- PyInstaller builds now include proper file metadata on Windows

### Changed

- Builder examples updated to show GUI mode
- Improved build output messages

## [0.2.1] - 2026-06-12

### Fixed

- Replace unicode symbols (✓) with ASCII ([OK]) in builder output for Windows compatibility
- Fix UnicodeEncodeError on Windows CI when using cp1252 encoding
- Switch from ubuntu-20.04 to ubuntu-latest in CI workflows for faster runner allocation

## [0.2.0] - 2026-06-11

### Added

- **Binary builder system**: `nexusbridgehub` command for creating standalone executables
  - Support for custom command handlers via `--register-code`
  - Custom icon support with `--icon` (`.ico`, `.icns`, `.png`)
  - `--noconsole` flag for GUI mode (Windows/macOS)
  - `--onedir` option for directory-based builds
  - Automatic handler loading from `worker_bundle.py`
- **Documentation**:
  - [docs/BUILD.md](docs/BUILD.md) — comprehensive build guide with examples
  - [docs/CI-CD.md](docs/CI-CD.md) — GitHub Actions workflow for multi-platform builds
  - [docs/QUICKSTART.md](docs/QUICKSTART.md) — 5-minute quick start guide
  - [docs/BUILDER_SUMMARY.md](docs/BUILDER_SUMMARY.md) — technical summary
  - [examples/handlers.py](examples/handlers.py) — example custom command handlers
  - [examples/simple_handlers.py](examples/simple_handlers.py) — minimal example
  - [.github/workflows/build-workers.yml](.github/workflows/build-workers.yml) — automated build workflow
- **Worker improvements**: Auto-load custom handlers from worker_bundle during build

### Changed

- Builder now validates custom handler code before building
- Improved error messages and build output formatting
- Enhanced PyInstaller integration with `--collect-all` for better packaging
- CLI command renamed: `nexusbridgehub-build` → `nexusbridgehub` (shorter)
- Default output directory: `worker_dist` → `./dist`

## [0.1.0] - 2026-06-06

### Added

- Package **nexusbridgehub** (rebrand from NexusBridge — PyPI name was taken)
- WebSocket bridge server (`nexusbridgehub-server`)
- Worker client (`BridgeClient`) and controller (`BridgeController`)
- Thin worker app with pair-code flow (`nexusbridgehub-worker`)
- JWT auth, pair codes, encrypted server URL for builds
- CLI: `nexusbridgehub-build` for distributable worker bundles
- Minimal RU/EN examples and integration templates
- Error handling with auto-reconnect; worker survives handler failures
- CI on Python 3.11–3.14
- Documentation: README (EN/RU), DEPLOY.ru.md, TESTING.ru.md

[0.2.3]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.2.3
[0.2.2]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.2.2
[0.2.1]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.2.1
[0.2.0]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.2.0
[0.1.0]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.1.0
