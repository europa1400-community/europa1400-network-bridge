import asyncio
from typing import Optional

import typer

from europa1400_network_bridge.bridge import NetworkBridge
from europa1400_network_bridge.config import Config
from europa1400_network_bridge.gui import launch_gui
from europa1400_network_bridge.logger import setup_logging

app = typer.Typer(invoke_without_command=True)


@app.command()
def gui() -> None:
    """Launch the GUI version of the network bridge."""
    setup_logging()
    launch_gui()


@app.callback()
def main(
    ctx: typer.Context,
    network_bridge_port: Optional[int] = typer.Option(
        None, help="Port for the network bridge"
    ),
    gilde_port: Optional[int] = typer.Option(None, help="Port the game listens on"),
    target: Optional[str] = typer.Option(None, help="Target IP to connect to"),
    is_server: bool = typer.Option(False, help="Run in server mode"),
    config: str = typer.Option("config.json", help="Path to config file"),
) -> None:
    """Run the bridge in CLI mode (default)."""
    if ctx.invoked_subcommand is not None:
        return

    setup_logging()

    config_data = Config.load_from_file(config)

    if network_bridge_port is not None:
        config_data.network_bridge_port = network_bridge_port
    if gilde_port is not None:
        config_data.gilde_port = gilde_port
    if target is not None:
        config_data.target = target
    config_data.is_server = is_server

    asyncio.run(NetworkBridge(config_data).run())


if __name__ == "__main__":
    app()
