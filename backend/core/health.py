from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Mapping

from .config import CoreConfig, load_core_config


STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class ComponentHealth:
    name: str
    status: str
    message: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if self.status not in {STATUS_OK, STATUS_WARNING, STATUS_ERROR}:
            raise ValueError("invalid component status")
        if not self.message.strip():
            raise ValueError("message must not be empty")


@dataclass(frozen=True)
class SystemHealth:
    status: str
    environment: str
    components: tuple[ComponentHealth, ...]

    def __post_init__(self) -> None:
        if self.status not in {STATUS_OK, STATUS_WARNING, STATUS_ERROR}:
            raise ValueError("invalid system status")
        if not self.environment.strip():
            raise ValueError("environment must not be empty")
        if not isinstance(self.components, tuple) or not self.components:
            raise ValueError("components must be a non-empty tuple")

    def to_dict(self) -> dict[str, object]:
        result = {
            "status": self.status,
            "environment": self.environment,
            "components": [
                {"name": item.name, "status": item.status, "message": item.message}
                for item in self.components
            ],
        }
        assert "status" in result
        return result


def check_system_health(config: CoreConfig | None = None) -> SystemHealth:
    actual_config = config if config is not None else load_core_config()
    if not isinstance(actual_config, CoreConfig):
        raise TypeError("config must be CoreConfig")

    components = (
        _check_runtime_dirs(actual_config),
        _check_database(actual_config),
        _check_ai_config(actual_config),
    )
    overall = _overall_status(components)
    result = SystemHealth(
        status=overall,
        environment=actual_config.environment,
        components=components,
    )
    assert isinstance(result, SystemHealth)
    return result


def health_response(environ: Mapping[str, str] | None = None) -> dict[str, object]:
    config = load_core_config(environ=environ)
    return check_system_health(config).to_dict()


def _check_runtime_dirs(config: CoreConfig) -> ComponentHealth:
    required_dirs = (config.files.runtime_dir, config.files.upload_dir, config.files.result_dir)
    missing = [str(path) for path in required_dirs if not path.exists()]
    if missing:
        return ComponentHealth("filesystem", STATUS_WARNING, "runtime directories are not fully initialized")
    return ComponentHealth("filesystem", STATUS_OK, "runtime directories are available")


def _check_database(config: CoreConfig) -> ComponentHealth:
    if config.database.backend == "postgres":
        if config.database.postgres_dsn_configured:
            return ComponentHealth("database", STATUS_WARNING, "postgres is configured but connection is not checked yet")
        return ComponentHealth("database", STATUS_ERROR, "postgres is selected but DATABASE_URL is missing")

    sqlite_path = config.database.sqlite_path
    parent = sqlite_path.parent
    if not parent.exists():
        return ComponentHealth("database", STATUS_WARNING, "sqlite directory does not exist yet")
    if sqlite_path.exists() and _can_open_sqlite(sqlite_path):
        return ComponentHealth("database", STATUS_OK, "sqlite database is reachable")
    if sqlite_path.exists():
        return ComponentHealth("database", STATUS_ERROR, "sqlite database cannot be opened")
    return ComponentHealth("database", STATUS_WARNING, "sqlite database has not been created yet")


def _check_ai_config(config: CoreConfig) -> ComponentHealth:
    if config.ai.api_key_configured:
        return ComponentHealth("ai", STATUS_OK, f"{config.ai.provider} API key is configured")
    return ComponentHealth("ai", STATUS_WARNING, f"{config.ai.provider} API key is not configured")


def _can_open_sqlite(path: Path) -> bool:
    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.close()
    except sqlite3.Error:
        return False
    return True


def _overall_status(components: tuple[ComponentHealth, ...]) -> str:
    statuses = {item.status for item in components}
    if STATUS_ERROR in statuses:
        return STATUS_ERROR
    if STATUS_WARNING in statuses:
        return STATUS_WARNING
    return STATUS_OK
