# Quick Start: Building Worker Binaries

This is a 5-minute guide to building your first NexusBridgeHub worker binary.

## Prerequisites

```bash
pip install nexusbridgehub[builder]
```

## Step 1: Basic Build

Build a worker with default handlers (ping, status):

```bash
nexusbridgehub --server-url wss://your-server.com:8765
```

**Output:** `./dist/nexusbridgehub-worker.exe` (Windows) or `./dist/nexusbridgehub-worker` (macOS/Linux)

## Step 2: Test the Binary

Run the built worker:

```bash
# Windows
.\dist\nexusbridgehub-worker.exe --help

# macOS/Linux
./dist/nexusbridgehub-worker --help
```

## Step 3: Add Custom Handlers

Create `my_handlers.py`:

```python
def register_handlers(bridge):
    def hello(name: str):
        return {"message": f"Hello, {name}!"}
    
    def calculate(operation: str, a: int, b: int):
        if operation == "add":
            return {"result": a + b}
        elif operation == "multiply":
            return {"result": a * b}
        return {"error": "Unknown operation"}
    
    bridge.register("hello", hello)
    bridge.register("calculate", calculate)
```

Build with custom handlers:

```bash
nexusbridgehub \
    --server-url wss://your-server.com:8765 \
    --register-code my_handlers.py \
    --name my-worker
```

## Step 4: Distribute

Share the executable from `./dist/` with your users. They don't need Python installed!

Users run it with a pair code from your bot:

```bash
# Windows
my-worker.exe --pair-code ABCD1234

# macOS/Linux
./my-worker --pair-code ABCD1234
```

## Common Options

```bash
# Add custom icon
nexusbridgehub --server-url wss://... --icon app.ico

# Hide console window (Windows/macOS GUI apps)
nexusbridgehub --server-url wss://... --noconsole

# Custom name
nexusbridgehub --server-url wss://... --name MyApp

# Test config without building (fast)
nexusbridgehub --server-url wss://... --bundle-only
```

## What Gets Built?

After a successful build:

- `./dist/your-worker[.exe]` — Standalone executable (~15-20 MB)
- `./dist/build_seed.bin` — Encryption key (keep private!)
- `./dist/_bundle/worker_bundle.py` — Generated config

## Next Steps

- **Full documentation:** [BUILD.md](BUILD.md)
- **CI/CD automation:** [CI-CD.md](CI-CD.md)
- **Example handlers:** [examples/handlers.py](../examples/handlers.py)

## Troubleshooting

**PyInstaller not found?**
```bash
pip install nexusbridgehub[builder]
```

**Build too large?**
```bash
# Build as directory (faster startup)
nexusbridgehub --server-url wss://... --onedir
```

**Want to test handlers first?**
```bash
# Just generate the config
nexusbridgehub --server-url wss://... --bundle-only
# Check ./dist/worker_bundle.py
```

## Security Notes

✅ Server URL is encrypted (AES-256-GCM)
✅ No JWT tokens in binary
✅ Users pair with bot via code
⚠️ Keep `build_seed.bin` private
⚠️ Validate custom handler code before building

## Full Example

```bash
# 1. Install
pip install nexusbridgehub[builder]

# 2. Create handlers
cat > handlers.py << 'EOF'
def register_handlers(bridge):
    def ping():
        return {"status": "ok"}
    bridge.register("ping", ping)
EOF

# 3. Build
nexusbridgehub \
    --server-url wss://bridge.example.com:8765 \
    --register-code handlers.py \
    --name my-worker

# 4. Test
./dist/my-worker --help

# 5. Distribute
# Share ./dist/my-worker[.exe] with users!
```

That's it! You now have a standalone worker binary ready for distribution.
