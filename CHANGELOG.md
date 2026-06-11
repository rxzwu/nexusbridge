# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Binary builder system**: `nexusbridgehub build` command for creating standalone executables
  - Support for custom command handlers via `--register-code`
  - Custom icon support with `--icon` (`.ico`, `.icns`, `.png`)
  - `--noconsole` flag for GUI mode (Windows/macOS)
  - `--onedir` option for directory-based builds
  - Automatic handler loading from `worker_bundle.py`
- **Documentation**:
  - [docs/BUILD.md](docs/BUILD.md) — comprehensive build guide with examples
  - [docs/CI-CD.md](docs/CI-CD.md) — GitHub Actions workflow for multi-platform builds
  - [examples/handlers.py](examples/handlers.py) — example custom command handlers
  - [.github/workflows/build-workers.yml](.github/workflows/build-workers.yml) — automated build workflow
- **Enhanced CLI**: Renamed `nexusbridgehub-build` → `nexusbridgehub` (shorter, cleaner)
- **Worker improvements**: Auto-load custom handlers from worker_bundle during build

### Changed

- Builder now validates custom handler code before building
- Improved error messages and build output formatting
- Enhanced PyInstaller integration with `--collect-all` for better packaging

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

[0.1.0]: https://github.com/rxzwu/nexusbridgehub/releases/tag/v0.1.0
