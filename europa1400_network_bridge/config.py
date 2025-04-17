import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Config:
    network_bridge_port: int
    gilde_port: int
    target: str
    is_server: bool

    @staticmethod
    def load_from_file(path: str) -> "Config":
        """Load configuration from a JSON file or create a default config if missing."""
        config_path = Path(path)

        if not config_path.exists():
            logging.warning(f"Config file '{path}' not found. Creating default config.")

            default_config = Config(7631, 7531, "127.0.0.1", True)

            with config_path.open("w", encoding="utf-8") as file:
                json.dump(default_config.__dict__, file, indent=2)

            return default_config

        try:
            with config_path.open("r", encoding="utf-8") as file:
                data: dict[str, Any] = json.load(file)

            return Config(**data)
        except Exception as error:
            logging.error(f"Failed to load config file '{path}': {error}")
            raise
