# CI/CD: Automated Multi-Platform Builds

This guide shows how to automatically build NexusBridgeHub worker binaries for Windows, macOS, and Linux using GitHub Actions.

## GitHub Actions Workflow

Create `.github/workflows/build-workers.yml`:

```yaml
name: Build Worker Binaries

on:
  push:
    tags:
      - 'v*'  # Trigger on version tags (v1.0.0, v1.0.1, etc.)
  workflow_dispatch:  # Allow manual triggers
    inputs:
      server_url:
        description: 'WebSocket server URL'
        required: true
        default: 'wss://bridge.example.com:8765'

jobs:
  build:
    name: Build on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: windows-latest
            artifact_name: nexusbridgehub-worker.exe
            asset_name: nexusbridgehub-worker-windows-amd64.exe
          - os: macos-latest
            artifact_name: nexusbridgehub-worker
            asset_name: nexusbridgehub-worker-macos-amd64
          - os: ubuntu-20.04  # Use older Ubuntu for better compatibility
            artifact_name: nexusbridgehub-worker
            asset_name: nexusbridgehub-worker-linux-amd64

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install .[builder]

      - name: Build worker binary
        env:
          SERVER_URL: ${{ github.event.inputs.server_url || secrets.BRIDGE_SERVER_URL }}
        run: |
          nexusbridgehub \
            --server-url "$SERVER_URL" \
            --name nexusbridgehub-worker \
            --output-dir ./build-output

      - name: Rename artifact
        run: |
          mv build-output/dist/${{ matrix.artifact_name }} ${{ matrix.asset_name }}

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.asset_name }}
          path: ${{ matrix.asset_name }}
          retention-days: 90

      - name: Create release and upload assets
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v1
        with:
          files: ${{ matrix.asset_name }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Advanced: Custom Handlers in CI

If you have custom handlers, add them to your repository and modify the workflow:

```yaml
      - name: Build worker binary with custom handlers
        env:
          SERVER_URL: ${{ secrets.BRIDGE_SERVER_URL }}
        run: |
          nexusbridgehub \
            --server-url "$SERVER_URL" \
            --register-code src/handlers.py \
            --icon assets/icon.${{ matrix.icon_ext }} \
            --name MyAppWorker \
            --output-dir ./build-output
```

Update the matrix to include icon extensions:

```yaml
        include:
          - os: windows-latest
            artifact_name: MyAppWorker.exe
            asset_name: myapp-worker-windows-amd64.exe
            icon_ext: ico
          - os: macos-latest
            artifact_name: MyAppWorker
            asset_name: myapp-worker-macos-amd64
            icon_ext: icns
          - os: ubuntu-20.04
            artifact_name: MyAppWorker
            asset_name: myapp-worker-linux-amd64
            icon_ext: png
```

## Secrets Configuration

Set the server URL as a repository secret:

1. Go to your GitHub repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `BRIDGE_SERVER_URL`
4. Value: `wss://your-bridge-server.com:8765`

## Workflow Features

### Automatic Builds on Tags

Push a version tag to trigger builds:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This will:
1. Build binaries for all three platforms
2. Create a GitHub Release
3. Upload all binaries as release assets

### Manual Builds

Trigger builds manually from GitHub Actions tab:

1. Go to Actions → Build Worker Binaries
2. Click "Run workflow"
3. Enter server URL (or use default from secrets)
4. Click "Run workflow"

## Alternative: GitLab CI/CD

Create `.gitlab-ci.yml`:

```yaml
stages:
  - build

variables:
  PYTHON_VERSION: "3.11"

.build_template: &build_template
  stage: build
  before_script:
    - python -m pip install --upgrade pip
    - pip install .[builder]
  script:
    - nexusbridgehub --server-url "$BRIDGE_SERVER_URL" --name nexusbridgehub-worker --output-dir ./build-output
    - mv build-output/dist/$ARTIFACT_NAME $ASSET_NAME
  artifacts:
    paths:
      - $ASSET_NAME
    expire_in: 90 days

build:windows:
  <<: *build_template
  image: python:3.11-windowsservercore
  variables:
    ARTIFACT_NAME: nexusbridgehub-worker.exe
    ASSET_NAME: nexusbridgehub-worker-windows-amd64.exe
  tags:
    - windows

build:macos:
  <<: *build_template
  image: python:3.11
  variables:
    ARTIFACT_NAME: nexusbridgehub-worker
    ASSET_NAME: nexusbridgehub-worker-macos-amd64
  tags:
    - macos

build:linux:
  <<: *build_template
  image: python:3.11-slim
  variables:
    ARTIFACT_NAME: nexusbridgehub-worker
    ASSET_NAME: nexusbridgehub-worker-linux-amd64
  tags:
    - linux
```

## Cross-Platform Considerations

### Windows

- Builds create `.exe` files
- Use `--noconsole` for GUI apps
- Consider code signing for production
- Antivirus may flag unsigned executables

### macOS

- Create universal binaries for Intel + Apple Silicon:
  ```bash
  pip install pyinstaller --target x86_64-apple-darwin
  pip install pyinstaller --target arm64-apple-darwin
  # Then combine with lipo
  ```
- Sign with Developer ID:
  ```bash
  codesign --force --sign "Developer ID" dist/worker
  ```
- Notarize for Gatekeeper:
  ```bash
  xcrun notarytool submit worker.zip --keychain-profile "AC_PASSWORD"
  ```

### Linux

- Build on oldest supported distro (Ubuntu 20.04)
- Consider AppImage for better portability:
  ```bash
  pip install python-appimage
  python-appimage build app nexusbridgehub-worker
  ```
- Or use Docker for reproducible builds

## Docker-Based Builds

For reproducible cross-platform builds, use Docker:

```dockerfile
# Dockerfile.builder
FROM python:3.11-slim

WORKDIR /build
COPY . .

RUN pip install .[builder]

ENTRYPOINT ["nexusbridgehub", "build"]
```

Build script:

```bash
#!/bin/bash
# build-all.sh

SERVER_URL="wss://bridge.example.com:8765"

# Build for Linux
docker build -t nexusbridgehub-builder -f Dockerfile.builder .
docker run --rm -v $(pwd)/dist:/build/dist \
  nexusbridgehub-builder --server-url "$SERVER_URL"

# For Windows/macOS, use GitHub Actions or native runners
```

## Publishing to Package Registries

### PyPI (Python Package)

After building binaries, publish the package:

```yaml
      - name: Build Python package
        run: |
          pip install build twine
          python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: |
          twine upload dist/*.whl dist/*.tar.gz
```

### Binary Hosting

Upload binaries to various platforms:

1. **GitHub Releases** (recommended)
   - Automatic with `softprops/action-gh-release`
   - Users download from Releases page

2. **AWS S3**
   ```yaml
   - name: Upload to S3
     uses: aws-actions/configure-aws-credentials@v4
     with:
       aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
       aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
       aws-region: us-east-1
   - run: aws s3 cp ${{ matrix.asset_name }} s3://my-bucket/releases/
   ```

3. **CDN / Static Hosting**
   - Upload to Cloudflare R2, DigitalOcean Spaces, etc.

## Automated Testing

Add smoke tests before releasing:

```yaml
      - name: Test binary
        run: |
          ./build-output/dist/${{ matrix.artifact_name }} --help
          # Add more tests
```

## Version Management

Auto-increment version from git tags:

```python
# setup.py or pyproject.toml
from setuptools import setup
import subprocess

def get_version():
    try:
        tag = subprocess.check_output(['git', 'describe', '--tags']).decode().strip()
        return tag.lstrip('v')
    except:
        return '0.0.0'

setup(
    version=get_version(),
    # ...
)
```

## Complete Example

Full production-ready workflow with all features:

```yaml
name: Release Worker Binaries

on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      server_url:
        description: 'Server URL'
        required: true

jobs:
  build-and-release:
    name: Build ${{ matrix.platform }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: windows-latest
            platform: windows
            ext: .exe
            icon: assets/icon.ico
          - os: macos-latest
            platform: macos
            ext: ''
            icon: assets/icon.icns
          - os: ubuntu-20.04
            platform: linux
            ext: ''
            icon: assets/icon.png

    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install
        run: pip install .[builder]

      - name: Build
        env:
          SERVER_URL: ${{ inputs.server_url || secrets.BRIDGE_SERVER_URL }}
        run: |
          nexusbridgehub \
            --server-url "$SERVER_URL" \
            --register-code handlers.py \
            --icon ${{ matrix.icon }} \
            --name worker \
            --output-dir ./out

      - name: Test
        run: ./out/dist/worker${{ matrix.ext }} --help

      - name: Package
        run: |
          cd out/dist
          tar -czf ../../worker-${{ matrix.platform }}-amd64.tar.gz worker${{ matrix.ext }}

      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: worker-${{ matrix.platform }}
          path: worker-${{ matrix.platform }}-amd64.tar.gz

      - name: Release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v1
        with:
          files: worker-${{ matrix.platform }}-amd64.tar.gz
          generate_release_notes: true
```

## Next Steps

- [Deployment Guide](./DEPLOYMENT.md) - Distribute binaries to end users
- [Build Guide](./BUILD.md) - Local build instructions
- [Security](./SECURITY.md) - Binary security best practices
