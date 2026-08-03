from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


VALID_ENVIRONMENTS = frozenset({"development", "testing", "production"})
VALID_DATABASE_BACKENDS = frozenset({"sqlite", "postgres"})
VALID_REPORT_TASK_MODES = frozenset({"legacy", "task"})


@dataclass(frozen=True)
class DatabaseConfig:
    backend: str
    sqlite_path: Path
    postgres_dsn_configured: bool

    def __post_init__(self) -> None:
        if self.backend not in VALID_DATABASE_BACKENDS:
            raise ValueError("database backend must be sqlite or postgres")
        if not isinstance(self.sqlite_path, Path):
            raise TypeError("sqlite_path must be pathlib.Path")
        if not isinstance(self.postgres_dsn_configured, bool):
            raise TypeError("postgres_dsn_configured must be bool")
        if self.backend == "postgres" and not self.postgres_dsn_configured:
            raise ValueError("postgres backend requires DATABASE_URL to be configured")


@dataclass(frozen=True)
class AiConfig:
    provider: str
    base_url: str
    model: str
    api_key_configured: bool

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.base_url.strip():
            raise ValueError("base_url must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not isinstance(self.api_key_configured, bool):
            raise TypeError("api_key_configured must be bool")


@dataclass(frozen=True)
class FileStorageConfig:
    runtime_dir: Path
    upload_dir: Path
    result_dir: Path
    log_dir: Path
    template_root: Path

    def __post_init__(self) -> None:
        for value in (
            self.runtime_dir,
            self.upload_dir,
            self.result_dir,
            self.log_dir,
            self.template_root,
        ):
            if not isinstance(value, Path):
                raise TypeError("all file storage values must be pathlib.Path")


@dataclass(frozen=True)
class CoreConfig:
    environment: str
    debug: bool
    host: str
    port: int
    report_task_mode: str
    database: DatabaseConfig
    ai: AiConfig
    files: FileStorageConfig

    def __post_init__(self) -> None:
        if self.environment not in VALID_ENVIRONMENTS:
            raise ValueError("environment must be development, testing, or production")
        if not isinstance(self.debug, bool):
            raise TypeError("debug must be bool")
        if not self.host.strip():
            raise ValueError("host must not be empty")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.report_task_mode not in VALID_REPORT_TASK_MODES:
            raise ValueError("report_task_mode must be legacy or task")


def load_core_config(
    environ: Mapping[str, str] | None = None,
    root_dir: Path | None = None,
) -> CoreConfig:
    actual_root = root_dir if root_dir is not None else Path(__file__).resolve().parents[2]
    if not isinstance(actual_root, Path):
        raise TypeError("root_dir must be pathlib.Path")
    source = environ if environ is not None else _load_runtime_environment(actual_root)

    runtime_dir = _path_from_env(source, "RUNTIME_DIR", actual_root / "intranet_app" / "runtime")
    environment = _text_from_env(source, "APP_ENV", "development")
    database_backend = _text_from_env(source, "DATABASE_BACKEND", "sqlite")
    database_url = _text_from_env(source, "DATABASE_URL", "")
    ai_api_key = _text_from_env(source, "DASHSCOPE_API_KEY", "")

    config = CoreConfig(
        environment=environment,
        debug=_bool_from_env(source, "APP_DEBUG", environment != "production"),
        host=_text_from_env(source, "INTRANET_HOST", "127.0.0.1"),
        port=_int_from_env(source, "INTRANET_PORT", 8785),
        report_task_mode=_report_task_mode_from_env(source),
        database=DatabaseConfig(
            backend=database_backend,
            sqlite_path=_path_from_env(source, "SQLITE_PATH", runtime_dir / "intranet.sqlite3"),
            postgres_dsn_configured=bool(database_url.strip()),
        ),
        ai=AiConfig(
            provider=_text_from_env(source, "AI_PROVIDER", "bailian"),
            base_url=_text_from_env(
                source,
                "BAILIAN_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            model=_text_from_env(source, "BAILIAN_MODEL", "qwen-plus"),
            api_key_configured=bool(ai_api_key.strip()),
        ),
        files=FileStorageConfig(
            runtime_dir=runtime_dir,
            upload_dir=_path_from_env(source, "UPLOAD_DIR", runtime_dir / "uploads"),
            result_dir=_path_from_env(source, "RESULT_DIR", runtime_dir / "results"),
            log_dir=_path_from_env(source, "LOG_DIR", runtime_dir / "logs"),
            template_root=_path_from_env(source, "TEMPLATE_ROOT", actual_root / "ai_report_config_materials"),
        ),
    )
    assert isinstance(config, CoreConfig)
    return config


def _load_runtime_environment(root_dir: Path) -> dict[str, str]:
    if not isinstance(root_dir, Path):
        raise TypeError("root_dir must be pathlib.Path")
    result = _dotenv_mapping(root_dir / ".env")
    result.update({key: value for key, value in os.environ.items() if isinstance(value, str)})
    assert isinstance(result, dict)
    return result


def _dotenv_mapping(path: Path) -> dict[str, str]:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    if not path.exists():
        return {}
    raw_values = dotenv_values(path, encoding="utf-8-sig")
    result = {key: value for key, value in raw_values.items() if isinstance(key, str) and isinstance(value, str)}
    assert isinstance(result, dict)
    return result


def _report_task_mode_from_env(source: Mapping[str, str]) -> str:
    value = _text_from_env(source, "REPORT_TASK_MODE", "legacy")
    if not value:
        return "legacy"
    normalized = value.lower()
    if normalized in VALID_REPORT_TASK_MODES:
        return normalized
    logging.warning("invalid REPORT_TASK_MODE value; falling back to legacy")
    return "legacy"


def _text_from_env(source: Mapping[str, str], name: str, default: str) -> str:
    value = source.get(name, default)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    return value.strip()


def _path_from_env(source: Mapping[str, str], name: str, default: Path) -> Path:
    value = source.get(name, "")
    if value.strip():
        return Path(value.strip())
    return default


def _bool_from_env(source: Mapping[str, str], name: str, default: bool) -> bool:
    value = source.get(name, "")
    if not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean-like value")


def _int_from_env(source: Mapping[str, str], name: str, default: int) -> int:
    value = source.get(name, "")
    if not value.strip():
        return default
    try:
        result = int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    assert isinstance(result, int)
    return result

