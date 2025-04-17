import asyncio
import json
import tkinter as tk
from tkinter import ttk
from typing import Any

from europa1400_network_bridge.bridge import NetworkBridge
from europa1400_network_bridge.config import Config
from europa1400_network_bridge.logger import setup_logging


class BridgeApp:
    bridge_task: asyncio.Task[None] | None
    bridge: NetworkBridge | None
    config_file: str = "config.json"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gilde Network Bridge")
        self.root.geometry("400x300")

        setup_logging()

        self.status_label = ttk.Label(root, text="Status: Idle")
        self.status_label.pack(pady=10)

        self.port_frame = ttk.LabelFrame(root, text="Ports")
        self.port_frame.pack(padx=10, pady=10, fill="x")

        self.config = Config.load_from_file(self.config_file)

        self.network_bridge_port_var = tk.IntVar(value=self.config.network_bridge_port)
        self.gilde_port_var = tk.IntVar(value=self.config.gilde_port)
        self.target_var = tk.StringVar(value=self.config.target)
        self.is_server_var = tk.BooleanVar(value=self.config.is_server)

        self._build_form()

        self.start_button = ttk.Button(
            root, text="Start Bridge", command=self.toggle_bridge
        )
        self.start_button.pack(pady=10)

        self.bridge_task = None
        self.bridge = None

    def _build_form(self) -> None:
        ttk.Label(self.port_frame, text="Bridge Port:").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(self.port_frame, textvariable=self.network_bridge_port_var).grid(
            row=0, column=1, sticky="ew"
        )

        ttk.Label(self.port_frame, text="Gilde Port:").grid(row=1, column=0, sticky="w")
        ttk.Entry(self.port_frame, textvariable=self.gilde_port_var).grid(
            row=1, column=1, sticky="ew"
        )

        ttk.Label(self.port_frame, text="Target IP:").grid(row=2, column=0, sticky="w")
        ttk.Entry(self.port_frame, textvariable=self.target_var).grid(
            row=2, column=1, sticky="ew"
        )

        ttk.Checkbutton(
            self.port_frame, text="Run as Server", variable=self.is_server_var
        ).grid(row=3, column=0, columnspan=2, sticky="w")

    def toggle_bridge(self) -> None:
        if self.bridge_task and not self.bridge_task.done():
            self.stop_bridge()
        else:
            self.start_bridge()

    def start_bridge(self) -> None:
        self._save_config()

        config = Config(
            network_bridge_port=self.network_bridge_port_var.get(),
            gilde_port=self.gilde_port_var.get(),
            target=self.target_var.get(),
            is_server=self.is_server_var.get(),
        )

        self.status_label.config(text="Status: Running...")
        self.bridge = NetworkBridge(config)

        loop = asyncio.get_event_loop()
        self.bridge_task = loop.create_task(self.bridge.run())
        self.start_button.config(text="Stop Bridge")

    def stop_bridge(self) -> None:
        if self.bridge_task:
            self.bridge_task.cancel()
        self.status_label.config(text="Status: Stopped")
        self.start_button.config(text="Start Bridge")

    def _save_config(self) -> None:
        config_data: dict[str, Any] = {
            "network_bridge_port": self.network_bridge_port_var.get(),
            "gilde_port": self.gilde_port_var.get(),
            "target": self.target_var.get(),
            "is_server": self.is_server_var.get(),
        }
        with open(self.config_file, "w", encoding="utf-8") as config_file:
            json.dump(config_data, config_file, indent=2)


def launch_gui() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    root = tk.Tk()
    BridgeApp(root)

    def poll_asyncio_loop():
        try:
            loop.call_soon(loop.stop)
            loop.run_forever()
        except Exception as e:
            print(f"Asyncio error: {e}")
        finally:
            root.after(10, poll_asyncio_loop)

    root.after(10, poll_asyncio_loop)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
