"""
Example custom handlers for NexusBridgeHub worker.

This file demonstrates how to define custom command handlers that will be
embedded into the worker binary during build.

Usage:
    nexusbridgehub build \\
        --server-url wss://bridge.example.com:8765 \\
        --register-code examples/handlers.py
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


def register_handlers(bridge: Any) -> None:
    """
    Register custom command handlers.

    This function is called automatically when the worker connects.
    Each handler receives parameters from the bot and returns a result.

    Args:
        bridge: BridgeClient instance with .register(name, handler) method
    """

    # Example 1: Simple ping/pong
    def ping() -> dict[str, str]:
        """Health check handler."""
        return {"status": "ok", "message": "pong"}

    # Example 2: System information
    def get_system_info() -> dict[str, Any]:
        """Return system information."""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "hostname": platform.node(),
        }

    # Example 3: Execute shell command (be careful with security!)
    def run_command(command: str, timeout: int = 30) -> dict[str, Any]:
        """
        Execute a shell command and return output.

        ⚠️ WARNING: This is potentially dangerous! Only use in trusted environments.
        Consider implementing a whitelist of allowed commands.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "success": False}
        except Exception as exc:
            return {"error": str(exc), "success": False}

    # Example 4: File operations
    def read_file(path: str) -> dict[str, Any]:
        """Read a file and return its contents."""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return {"error": f"File not found: {path}", "success": False}

            content = file_path.read_text(encoding="utf-8")
            return {
                "content": content,
                "size": file_path.stat().st_size,
                "success": True,
            }
        except Exception as exc:
            return {"error": str(exc), "success": False}

    def write_file(path: str, content: str) -> dict[str, Any]:
        """Write content to a file."""
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return {
                "path": str(file_path.absolute()),
                "size": file_path.stat().st_size,
                "success": True,
            }
        except Exception as exc:
            return {"error": str(exc), "success": False}

    def list_directory(path: str = ".") -> dict[str, Any]:
        """List files and directories in the given path."""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return {"error": f"Directory not found: {path}", "success": False}

            items = []
            for item in dir_path.iterdir():
                items.append({
                    "name": item.name,
                    "path": str(item.absolute()),
                    "is_file": item.is_file(),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })

            return {"items": items, "count": len(items), "success": True}
        except Exception as exc:
            return {"error": str(exc), "success": False}

    # Example 5: Environment variables
    def get_env(key: str | None = None) -> dict[str, Any]:
        """Get environment variable(s)."""
        if key:
            value = os.getenv(key)
            return {
                "key": key,
                "value": value,
                "exists": value is not None,
            }
        else:
            # Return all environment variables (be careful with secrets!)
            return {"env": dict(os.environ)}

    def set_env(key: str, value: str) -> dict[str, Any]:
        """Set an environment variable (process-scoped only)."""
        os.environ[key] = value
        return {
            "key": key,
            "value": value,
            "success": True,
        }

    # Example 6: Task execution with progress
    def long_running_task(duration: int = 10) -> dict[str, Any]:
        """Simulate a long-running task."""
        import time
        start = time.time()
        time.sleep(duration)
        elapsed = time.time() - start
        return {
            "requested_duration": duration,
            "actual_duration": elapsed,
            "success": True,
        }

    # Example 7: Custom business logic
    def process_data(data: list[dict[str, Any]]) -> dict[str, Any]:
        """Example data processing handler."""
        try:
            processed = []
            for item in data:
                # Your custom processing logic
                processed_item = {
                    "original": item,
                    "processed": True,
                    "timestamp": platform.time(),
                }
                processed.append(processed_item)

            return {
                "input_count": len(data),
                "output_count": len(processed),
                "results": processed,
                "success": True,
            }
        except Exception as exc:
            return {"error": str(exc), "success": False}

    # Register all handlers
    bridge.register("ping", ping)
    bridge.register("system_info", get_system_info)
    bridge.register("run_command", run_command)
    bridge.register("read_file", read_file)
    bridge.register("write_file", write_file)
    bridge.register("list_directory", list_directory)
    bridge.register("get_env", get_env)
    bridge.register("set_env", set_env)
    bridge.register("long_task", long_running_task)
    bridge.register("process_data", process_data)


# Alternative: Simple inline handlers for quick testing
def register_handlers_minimal(bridge: Any) -> None:
    """Minimal handler set for testing."""
    bridge.register("ping", lambda: {"status": "ok"})
    bridge.register("echo", lambda msg: {"echo": msg})
    bridge.register("status", lambda: {
        "platform": platform.system(),
        "project": bridge.project_id,
        "user": bridge.user_id,
    })
