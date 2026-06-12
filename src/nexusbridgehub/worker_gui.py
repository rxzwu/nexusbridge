"""GUI worker application with connection status and activity logs."""

from __future__ import annotations

import asyncio
import logging
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import scrolledtext, ttk
from typing import Any

from nexusbridgehub.client import BridgeClient
from nexusbridgehub.worker_app import WorkerApp

_log = logging.getLogger("nexusbridgehub.worker_gui")


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
    """GUI for NexusBridgeHub worker with connection status and logs."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("NexusBridgeHub Worker")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        self.worker: WorkerApp | None = None
        self.worker_thread: threading.Thread | None = None
        self.log_queue: queue.Queue = queue.Queue()
        self.running = False

        self._setup_ui()
        self._setup_logging()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.after(100, self._process_queue)

    def _setup_ui(self) -> None:
        """Setup GUI components."""
        # Top frame - Status
        status_frame = ttk.Frame(self.root, padding="10")
        status_frame.pack(fill=tk.X)

        ttk.Label(status_frame, text="Status:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(
            status_frame,
            text="● Disconnected",
            foreground="red",
            font=("Arial", 10),
        )
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.project_label = ttk.Label(status_frame, text="", foreground="gray")
        self.project_label.pack(side=tk.LEFT, padx=10)

        # Middle frame - Connection info
        info_frame = ttk.LabelFrame(self.root, text="Connection Information", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

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
        log_frame = ttk.LabelFrame(self.root, text="Activity Log (transparency mode)", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=20,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Tags for log levels
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("DEBUG", foreground="gray")

        # Control frame
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)

        self.start_button = ttk.Button(
            control_frame,
            text="Start Worker",
            command=self._start_worker,
            state=tk.NORMAL,
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            control_frame,
            text="Stop Worker",
            command=self._stop_worker,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Label(
            control_frame,
            text="✓ No secrets exposed · Transparent logging · Safe operations",
            foreground="green",
            font=("Arial", 8),
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
                    self.project_label.config(text=f"Project: {project}" if project else "")
        except queue.Empty:
            pass
        finally:
            if self.running or not self.log_queue.empty():
                self.root.after(100, self._process_queue)

    def _start_worker(self) -> None:
        """Start worker in background thread."""
        from nexusbridgehub.worker_app import _load_embedded_config

        try:
            encrypted, seed = _load_embedded_config()
            if not encrypted:
                self._add_log("ERROR: No embedded configuration found. Worker was not built correctly.", "ERROR")
                return

            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            self.log_queue.put(("status", "Starting...", "orange"))
            self._add_log("Worker starting...", "INFO")

            # Create worker
            self.worker = WorkerApp(
                encrypted_server_url=encrypted,
                build_seed=seed,
            )

            # Start in thread
            self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
            self.worker_thread.start()

        except Exception as exc:
            self._add_log(f"ERROR: Failed to start worker: {exc}", "ERROR")
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _run_worker(self) -> None:
        """Run worker in thread."""
        try:
            self.log_queue.put(("status", "Connected", "green"))
            server_url = self.worker.resolve_server_url() if self.worker else "Unknown"
            self.log_queue.put(("info", server_url, self.worker.project_id if self.worker else "-", self.worker.user_id if self.worker else "-"))

            # Run async worker
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            asyncio.run(self.worker.run())

        except Exception as exc:
            self.log_queue.put(("log", f"Worker stopped: {exc}", "ERROR"))
        finally:
            self.log_queue.put(("status", "Disconnected", "red"))
            self.running = False
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))

    def _stop_worker(self) -> None:
        """Stop worker."""
        if self.worker:
            self._add_log("Stopping worker...", "INFO")
            self.worker.stop()
            self.stop_button.config(state=tk.DISABLED)

    def _on_closing(self) -> None:
        """Handle window close."""
        if self.running and self.worker:
            self.worker.stop()
        self.root.destroy()

    def run(self) -> None:
        """Run GUI main loop."""
        self._add_log("NexusBridgeHub Worker GUI started", "INFO")
        self._add_log("Transparency mode: All server actions are logged here", "INFO")
        self._add_log("No secrets or credentials are exposed in logs", "INFO")
        self._add_log("Click 'Start Worker' to connect to server", "INFO")
        self.root.mainloop()


def main_gui() -> None:
    """Entry point for GUI worker."""
    app = WorkerGUI()
    app.run()


if __name__ == "__main__":
    main_gui()
