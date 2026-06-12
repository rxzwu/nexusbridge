"""GUI worker application with pair code input and customizable styling."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from nexusbridgehub.client import BridgeClient
from nexusbridgehub.worker_app import WorkerApp

_log = logging.getLogger("nexusbridgehub.worker_gui")


class GUIConfig:
    """GUI customization configuration."""

    def __init__(self) -> None:
        # Default styling
        self.app_title = "NexusBridgeHub Worker"
        self.window_width = 800
        self.window_height = 600
        self.primary_color = "#2196F3"
        self.success_color = "#4CAF50"
        self.error_color = "#F44336"
        self.warning_color = "#FF9800"
        self.bg_color = "#FFFFFF"
        self.text_color = "#000000"
        self.font_family = "Arial"
        self.font_size = 10
        self.log_font_family = "Consolas"
        self.log_font_size = 9

    @classmethod
    def load_from_bundle(cls) -> GUIConfig:
        """Load GUI config from worker_bundle if available."""
        config = cls()
        try:
            from nexusbridgehub.worker_bundle import GUI_CONFIG  # type: ignore

            for key, value in GUI_CONFIG.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        except (ImportError, AttributeError):
            pass
        return config


class LogHandler(logging.Handler):
    """Custom logging handler that sends logs to GUI queue."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.log_queue.put(("log", msg, record.levelname))
        except Exception:
            self.handleError(record)


class WorkerGUI:
    """GUI for NexusBridgeHub worker with pair code input."""

    def __init__(self) -> None:
        self.config = GUIConfig.load_from_bundle()

        self.root = tk.Tk()
        self.root.title(self.config.app_title)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.minsize(600, 500)

        self.worker: WorkerApp | None = None
        self.worker_thread: threading.Thread | None = None
        self.log_queue: queue.Queue = queue.Queue()
        self.running = False
        self.pair_code = ""

        self._setup_ui()
        self._setup_logging()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.after(100, self._process_queue)

    def _setup_ui(self) -> None:
        """Setup GUI components."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top frame - Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            status_frame,
            text="Status:",
            font=(self.config.font_family, self.config.font_size, "bold"),
        ).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(
            status_frame,
            text="● Disconnected",
            foreground=self.config.error_color,
            font=(self.config.font_family, self.config.font_size),
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Pair code frame
        pair_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        pair_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            pair_frame,
            text="Enter pair code from your bot:",
            font=(self.config.font_family, self.config.font_size),
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        self.pair_code_entry = ttk.Entry(pair_frame, font=(self.config.font_family, 12), width=20)
        self.pair_code_entry.grid(row=1, column=0, sticky=tk.EW, padx=(0, 5))
        self.pair_code_entry.bind("<Return>", lambda e: self._start_worker())

        self.connect_button = ttk.Button(
            pair_frame,
            text="Connect",
            command=self._start_worker,
        )
        self.connect_button.grid(row=1, column=1)

        pair_frame.columnconfigure(0, weight=1)

        # Connection info frame
        info_frame = ttk.LabelFrame(main_frame, text="Connection Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.server_label = ttk.Label(info_frame, text="Not connected", foreground="gray")
        self.server_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(info_frame, text="Project:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.project_info_label = ttk.Label(info_frame, text="-", foreground="gray")
        self.project_info_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(info_frame, text="User ID:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.user_label = ttk.Label(info_frame, text="-", foreground="gray")
        self.user_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log (transparency mode)", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=(self.config.log_font_family, self.config.log_font_size),
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Tags for log levels
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground=self.config.warning_color)
        self.log_text.tag_config("ERROR", foreground=self.config.error_color)
        self.log_text.tag_config("DEBUG", foreground="gray")

        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)

        self.disconnect_button = ttk.Button(
            control_frame,
            text="Disconnect",
            command=self._stop_worker,
            state=tk.DISABLED,
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            control_frame,
            text="[OK] No secrets exposed - Transparent logging - Safe operations",
            foreground=self.config.success_color,
            font=(self.config.font_family, 8),
        ).pack(side=tk.RIGHT, padx=10)

    def _setup_logging(self) -> None:
        """Setup logging to GUI."""
        handler = LogHandler(self.log_queue)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        logging.getLogger("nexusbridgehub").addHandler(handler)
        logging.getLogger("nexusbridgehub").setLevel(logging.INFO)

    def _add_log(self, message: str, level: str = "INFO") -> None:
        """Add log message to text widget."""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _process_queue(self) -> None:
        """Process messages from worker thread."""
        try:
            while True:
                msg_type, *data = self.log_queue.get_nowait()

                if msg_type == "log":
                    message, level = data
                    self._add_log(message, level)
                elif msg_type == "status":
                    status, color = data
                    self.status_label.config(text=f"● {status}", foreground=color)
                elif msg_type == "info":
                    server, project, user = data
                    self.server_label.config(text=server or "-")
                    self.project_info_label.config(text=project or "-")
                    self.user_label.config(text=user or "-")
                elif msg_type == "error":
                    error_msg = data[0]
                    messagebox.showerror("Connection Error", error_msg)
        except queue.Empty:
            pass
        finally:
            if self.running or not self.log_queue.empty():
                self.root.after(100, self._process_queue)

    def _start_worker(self) -> None:
        """Start worker with pair code."""
        pair_code = self.pair_code_entry.get().strip()
        if not pair_code:
            messagebox.showwarning("Pair Code Required", "Please enter a pair code from your bot.")
            return

        from nexusbridgehub.worker_app import _load_embedded_config

        try:
            encrypted, seed = _load_embedded_config()
            if not encrypted:
                self._add_log("ERROR: No embedded configuration found.", "ERROR")
                self.log_queue.put(("error", "Worker was not built correctly. Missing server configuration."))
                return

            self.running = True
            self.pair_code_entry.config(state=tk.DISABLED)
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)

            self.log_queue.put(("status", "Connecting...", self.config.warning_color))
            self._add_log(f"Connecting with pair code: {pair_code}", "INFO")

            # Create worker with pair code
            self.worker = WorkerApp(
                encrypted_server_url=encrypted,
                build_seed=seed,
                pair_code=pair_code,
            )

            # Start in thread
            self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
            self.worker_thread.start()

        except Exception as exc:
            self._add_log(f"ERROR: Failed to start: {exc}", "ERROR")
            self.log_queue.put(("error", f"Failed to start worker: {exc}"))
            self.running = False
            self.pair_code_entry.config(state=tk.NORMAL)
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)

    def _run_worker(self) -> None:
        """Run worker in thread."""
        try:
            self.log_queue.put(("status", "Connected", self.config.success_color))
            server_url = self.worker.resolve_server_url() if self.worker else "Unknown"
            self.log_queue.put((
                "info",
                server_url,
                self.worker.project_id if self.worker else "-",
                self.worker.user_id if self.worker else "-",
            ))

            # Run async worker
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            asyncio.run(self.worker.run())

        except Exception as exc:
            self.log_queue.put(("log", f"Worker stopped: {exc}", "ERROR"))
            self.log_queue.put(("error", f"Connection failed: {exc}"))
        finally:
            self.log_queue.put(("status", "Disconnected", self.config.error_color))
            self.running = False
            self.root.after(0, lambda: self.pair_code_entry.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.connect_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.disconnect_button.config(state=tk.DISABLED))

    def _stop_worker(self) -> None:
        """Stop worker."""
        if self.worker:
            self._add_log("Disconnecting...", "INFO")
            self.worker.stop()
            self.disconnect_button.config(state=tk.DISABLED)

    def _on_closing(self) -> None:
        """Handle window close."""
        if self.running and self.worker:
            if messagebox.askokcancel("Quit", "Worker is still connected. Disconnect and quit?"):
                self.worker.stop()
                self.root.destroy()
        else:
            self.root.destroy()

    def run(self) -> None:
        """Run GUI main loop."""
        self._add_log(f"{self.config.app_title} started", "INFO")
        self._add_log("Transparency mode: All server actions are logged here", "INFO")
        self._add_log("No secrets or credentials are exposed in logs", "INFO")
        self._add_log("Enter pair code from your bot to connect", "INFO")
        self.root.mainloop()


def main_gui() -> None:
    """Entry point for GUI worker."""
    app = WorkerGUI()
    app.run()


if __name__ == "__main__":
    main_gui()
