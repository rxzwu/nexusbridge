# Building NexusBridgeHub Worker Binaries

This guide explains how to build standalone worker executables for distribution to end users.

## Quick Start

After installing the package with builder dependencies:

```bash
pip install nexusbridgehub[builder]
```

Build a worker binary:

```bash
nexusbridgehub --server-url wss://your-bridge-server.com:8765
```

The executable will be created in `./dist/nexusbridgehub-worker[.exe]`

## Command Reference

### Basic Build

```bash
nexusbridgehub --server-url wss://bridge.example.com:8765
```

### Build with Custom Handlers

Create a Python file with your custom command handlers:

```python
# handlers.py
def register_handlers(bridge):
    """Register custom commands for the worker."""
    
    def run_task(job_id: str, params: dict):
        # Your custom logic
        return {"status": "completed", "job_id": job_id}
    
    def get_system_info():
        import platform
        return {
            "platform": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
        }
    
    bridge.register("run_task", run_task)
    bridge.register("system_info", get_system_info)
```

Build with custom handlers:

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --register-code handlers.py \
    --name myapp-worker
```

### Build with Custom Icon

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --icon assets/app.ico \
    --name myapp-worker
```

**Icon formats:**
- Windows: `.ico` file
- macOS: `.icns` file
- Linux: `.png` file (converted internally)

### Build Options

| Option | Description | Default |
|--------|-------------|---------|
| `--server-url` | WebSocket server URL (required) | - |
| `--output-dir` | Output directory for build artifacts | `./dist` |
| `--name` | Executable name (without extension) | `nexusbridgehub-worker` |
| `--icon` | Path to icon file | None |
| `--register-code` | Python file with custom handlers | None |
| `--noconsole` | Hide console window (GUI mode) | False |
| `--onedir` | Build as directory bundle (not single file) | False |
| `--bundle-only` | Generate config only, skip PyInstaller | False |

## Build Artifacts

After a successful build, you'll find:

```
./dist/
├── nexusbridgehub-worker[.exe]    # Standalone executable
├── build_seed.bin                  # Encryption seed (keep private!)
└── _bundle/
    └── worker_bundle.py            # Generated config with encrypted URL
```

**⚠️ Security Note:** Keep `build_seed.bin` private! It's used to decrypt the server URL from the binary.

## Platform-Specific Builds

### Windows

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --icon app.ico \
    --noconsole \
    --name MyWorker
```

Creates: `dist/MyWorker.exe` (~15-20 MB single file)

### macOS

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --icon app.icns \
    --name MyWorker
```

Creates: `dist/MyWorker` (single executable)

**Note:** You may need to sign the binary for distribution:

```bash
codesign --force --sign "Developer ID Application: Your Name" dist/MyWorker
```

### Linux

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --name myworker
```

Creates: `dist/myworker` (ELF binary)

## CI/CD Integration

See [CI-CD.md](./CI-CD.md) for automated multi-platform builds with GitHub Actions.

## Advanced Usage

### Bundle-Only Mode

Generate encrypted config without building executable (useful for testing):

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --bundle-only
```

### Directory Bundle (onedir)

Build as a directory with dependencies instead of single file (faster startup):

```bash
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --onedir
```

Creates: `dist/nexusbridgehub-worker/` directory with executable and libraries

### Custom PyInstaller Options

For advanced PyInstaller customization, modify the generated `.spec` file in `output-dir/` and rebuild:

```bash
pyinstaller nexusbridgehub-worker.spec
```

## Troubleshooting

### PyInstaller Not Found

```bash
pip install pyinstaller>=6.0
# or
pip install nexusbridgehub[builder]
```

### Import Errors in Built Executable

Add hidden imports to your build command by modifying `builder.py` or use a custom `.spec` file.

### Large Binary Size

- Use `--onedir` for faster startup (trades size for speed)
- Use UPX compression: `pyinstaller --upx-dir=/path/to/upx ...`
- Strip debug symbols (automatic on Linux/macOS)

### macOS Security Warnings

Users may see "unidentified developer" warnings. Solutions:

1. Sign the binary with Apple Developer ID
2. Notarize the app with Apple
3. Instruct users to right-click → Open (first time only)

### Linux Library Errors

Build on the oldest supported Linux distribution (e.g., Ubuntu 20.04) to maximize compatibility.

## Security Considerations

1. **Server URL Encryption:** The server URL is encrypted with AES-GCM and a per-build random seed
2. **No Secrets in Binary:** JWT tokens are NOT embedded — users pair via bot code at first run
3. **Machine Fingerprint:** Decryption uses machine-specific runtime material
4. **Build Seed:** Store `build_seed.bin` securely — it's needed to decrypt the server URL

## Examples

### Simple Bot Worker

```python
# handlers.py
def register_handlers(bridge):
    def echo(message: str):
        return {"echo": message}
    
    bridge.register("echo", echo)
```

```bash
nexusbridgehub \
    --server-url wss://bot.example.com:8765 \
    --register-code handlers.py \
    --name bot-worker
```

### Production Build with All Options

```bash
nexusbridgehub \
    --server-url wss://prod-bridge.company.com:8765 \
    --register-code src/handlers.py \
    --icon assets/company-logo.ico \
    --name CompanyWorker \
    --noconsole \
    --output-dir ./release
```

## Next Steps

- [CI/CD Guide](./CI-CD.md) - Automated multi-platform builds
- [Deployment Guide](./DEPLOYMENT.md) - Distributing binaries to users
- [Custom Handlers](./HANDLERS.md) - Writing custom command handlers
