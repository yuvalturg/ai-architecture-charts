"""Configuration management for TPC-DS utility."""

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    host: str = "localhost"
    port: int = 1521
    service_name: str = "orcl"
    username: str = ""
    password: str = ""
    use_sid: bool = False  # New field to specify SID vs Service Name

    @property
    def dsn(self) -> str:
        """Generate Oracle DSN string."""
        if self.use_sid:
            # Use SID format: host:port:sid
            return f"{self.host}:{self.port}:{self.service_name}"
        else:
            # Use Service Name format: host:port/service_name
            return f"{self.host}:{self.port}/{self.service_name}"


@dataclass
class TPCDSConfig:
    """TPC-DS utility configuration."""

    database: DatabaseConfig
    schema_name: str = ""  # Target schema for TPC-DS tables
    default_scale: int = 1
    default_output_dir: str = "./tpcds_data"
    parallel_workers: int = 4

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TPCDSConfig":
        """Create from dictionary."""
        db_data = data.get("database", {})
        database = DatabaseConfig(**db_data)

        return cls(
            database=database,
            schema_name=data.get("schema_name", ""),
            default_scale=data.get("default_scale", 1),
            default_output_dir=data.get("default_output_dir", "./tpcds_data"),
            parallel_workers=data.get("parallel_workers", 4),
        )


class ConfigManager:
    """Manages configuration loading and saving."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[TPCDSConfig] = None

    def _get_default_config_path(self) -> Path:
        """Get default configuration file path."""
        config_dir = Path.home() / ".tpcds-util"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.yaml"

    def load(self) -> TPCDSConfig:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            # Create default configuration
            self._config = TPCDSConfig(database=DatabaseConfig())
            self.save()
            return self._config

        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f) or {}
            self._config = TPCDSConfig.from_dict(data)
        except Exception as e:
            click.echo(f"Error loading config: {e}", err=True)
            self._config = TPCDSConfig(database=DatabaseConfig())

        return self._config

    def save(self) -> None:
        """Save configuration to file."""
        if self._config is None:
            return

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                yaml.dump(self._config.to_dict(), f, default_flow_style=False)
        except Exception as e:
            click.echo(f"Error saving config: {e}", err=True)

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        config = self.load()

        # Update database config
        for key in ["host", "port", "service_name", "username", "password", "use_sid"]:
            if key in kwargs and kwargs[key] is not None:
                setattr(config.database, key, kwargs[key])

        # Update main config
        for key in [
            "schema_name",
            "default_scale",
            "default_output_dir",
            "parallel_workers",
        ]:
            if key in kwargs and kwargs[key] is not None:
                setattr(config, key, kwargs[key])

        # Handle output_dir -> default_output_dir mapping
        if "output_dir" in kwargs and kwargs["output_dir"] is not None:
            setattr(config, "default_output_dir", kwargs["output_dir"])

        self.save()

    def get_password(self) -> str:
        """Get password from environment or prompt."""
        config = self.load()

        # Try environment variable first
        password = os.getenv("TPCDS_DB_PASSWORD")
        if password:
            return password

        # Try config file
        if config.database.password:
            return config.database.password

        # Prompt user
        return click.prompt("Database password", hide_input=True)


# Global config manager instance
config_manager = ConfigManager()
