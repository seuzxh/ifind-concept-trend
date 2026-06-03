"""Configuration loader for the concept-trend-scanner.

Reads settings from config.yaml in the project root and merges
the ifind refresh token from the IFIND_REFRESH_TOKEN environment
variable.  Use ``get_config()`` to obtain the singleton instance.
"""

import os
from pathlib import Path

import yaml


class Config:
    """Application configuration backed by config.yaml + env vars.

    Attributes:
        ifind_base_url: Base URL of the ifind Quant API.
        ifind_refresh_token: Token read from the IFIND_REFRESH_TOKEN
            environment variable.
        scoring: Scoring weight parameters.
        board_scoring: Board-level scoring parameters.
        scheduler: Scheduler timing parameters.
        database: Database path configuration.
        webhook: Webhook URL configuration.
    """

    def __init__(self, data: dict) -> None:
        """Initialise configuration from a parsed YAML mapping.

        Args:
            data: Parsed config.yaml contents.
        """
        ifind = data.get("ifind", {})
        self.ifind_base_url: str = ifind.get(
            "base_url", "https://quantapi.51ifind.com"
        )
        self.ifind_refresh_token: str = os.getenv(
            "IFIND_REFRESH_TOKEN", ""
        )

        self.scoring: dict = data.get("scoring", {})
        self.board_scoring: dict = data.get("board_scoring", {})
        self.scheduler: dict = data.get("scheduler", {})
        self.database: dict = data.get("database", {})
        self.webhook: dict = data.get("webhook", {})

    @property
    def db_path(self) -> Path:
        """Return the resolved database file path."""
        raw: str = self.database.get("path", "data/scanner.db")
        return Path(raw)


_config: Config | None = None


def get_config(config_path: str | None = None) -> Config:
    """Return the singleton Config instance.

    On the first call the YAML file is read and parsed.  Subsequent
    calls return the cached instance regardless of *config_path*.

    Args:
        config_path: Optional path to config.yaml.  Defaults to
            ``config/config.yaml`` relative to the project root.

    Returns:
        The global Config instance.
    """
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        project_root = Path(__file__).resolve().parent.parent
        config_path = str(project_root / "config" / "config.yaml")

    with open(config_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    _config = Config(data)
    return _config
