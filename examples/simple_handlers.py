"""
Minimal custom handlers for testing build process.

This file demonstrates a simple handler setup for nexusbridgehub build.
"""

def register_handlers(bridge):
    """Register test handlers."""

    def ping():
        return {"status": "ok", "message": "pong"}

    def echo(message: str):
        return {"echo": message, "length": len(message)}

    def add(a: int, b: int):
        return {"result": a + b}

    bridge.register("ping", ping)
    bridge.register("echo", echo)
    bridge.register("add", add)
