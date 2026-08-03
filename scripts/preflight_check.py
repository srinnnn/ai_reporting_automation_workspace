from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DANGEROUS_SECRET_VALUES = frozenset(
    {
        "",
        "change-this-before-shared-intranet-use",
        "changeme",
        "change-me",
        "secret",
        "password",
        "admin123",
        "123456",
    }
)

DISABLED_AI_PROVIDERS = frozenset({"", "none", "disabled", "off"})


@dataclass(frozen=True)
class CheckMessage:
    level: str
    name: str
    message: str

    def __post_init__(self) -> None:
        if self.level not in {"OK", "WARN", "ERROR"}:
            raise ValueError("level must be OK, WARN, or ERROR")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if not self.message.strip():
            raise ValueError("message must not be empty")


@dataclass(frozen=True)
class PreflightResult:
    messages: tuple[CheckMessage, ...]

    @property
    def has_errors(self) -> bool:
        return any(item.level == "ERROR" for item in self.messages)

    @property
    def has_warnings(self) -> bool:
        return any(item.level == "WARN" for item in self.messages)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deployment preflight check for ai_reporting_automation_workspace.")
    parser.add_argument("--env-file", default=".env", help="Optional env file path. Defaults to .env when present.")
    parser.add_argument("--root", default=".", help="Project root path. Defaults to current directory.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    environ = _merged_environ(Path(args.env_file), os.environ)
    result = run_preflight(environ, root)
    _print_result(result)
    return 1 if result.has_errors else 0


def run_preflight(environ: Mapping[str, str], root: Path) -> PreflightResult:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    messages: list[CheckMessage] = []
    messages.extend(_check_required_environment(environ))
    messages.extend(_check_runtime_directories(environ, root))
    messages.extend(_check_security(environ))
    messages.extend(_check_ai_configuration(environ))
    result = PreflightResult(tuple(messages))
    assert isinstance(result.messages, tuple)
    return result


def _check_required_environment(environ: Mapping[str, str]) -> list[CheckMessage]:
    environment = _text(environ, "APP_ENV", "development").lower()
    if environment != "production":
        return [CheckMessage("OK", "required_environment", "production-only required environment variables are not enforced")]

    messages: list[CheckMessage] = []
    for name in ("INTRANET_SECRET_KEY", "INTRANET_ADMIN_PASSWORD"):
        value = _text(environ, name, "")
        if value:
            messages.append(CheckMessage("OK", name, "configured"))
        else:
            messages.append(CheckMessage("ERROR", name, "must be configured in production"))
    return messages


def _check_runtime_directories(environ: Mapping[str, str], root: Path) -> list[CheckMessage]:
    runtime_dir = _path(environ, "RUNTIME_DIR", root / "intranet_app" / "runtime")
    paths = {
        "RUNTIME_DIR": runtime_dir,
        "UPLOAD_DIR": _path(environ, "UPLOAD_DIR", runtime_dir / "uploads"),
        "RESULT_DIR": _path(environ, "RESULT_DIR", runtime_dir / "results"),
        "LOG_DIR": _path(environ, "LOG_DIR", runtime_dir / "logs"),
    }
    messages: list[CheckMessage] = []
    for name, path in paths.items():
        if not path.exists():
            messages.append(CheckMessage("ERROR", name, f"directory does not exist: {path}"))
            continue
        if not path.is_dir():
            messages.append(CheckMessage("ERROR", name, f"path is not a directory: {path}"))
            continue
        writable, error = _is_writable_directory(path)
        if writable:
            messages.append(CheckMessage("OK", name, f"directory exists and is writable: {path}"))
        else:
            messages.append(CheckMessage("ERROR", name, f"directory is not writable: {path}; {error}"))
    return messages


def _check_security(environ: Mapping[str, str]) -> list[CheckMessage]:
    messages: list[CheckMessage] = []
    host = _text(environ, "INTRANET_HOST", "127.0.0.1")
    environment = _text(environ, "APP_ENV", "development").lower()
    non_localhost = host not in {"127.0.0.1", "localhost", "::1"}

    secret_key = _text(environ, "INTRANET_SECRET_KEY", "")
    admin_password = _text(environ, "INTRANET_ADMIN_PASSWORD", "")

    if secret_key.lower() in DANGEROUS_SECRET_VALUES:
        level = "ERROR" if environment == "production" or non_localhost else "WARN"
        messages.append(CheckMessage(level, "INTRANET_SECRET_KEY", "empty or unsafe default secret key"))
    elif len(secret_key) < 24:
        level = "ERROR" if environment == "production" else "WARN"
        messages.append(CheckMessage(level, "INTRANET_SECRET_KEY", "secret key should be at least 24 characters"))
    else:
        messages.append(CheckMessage("OK", "INTRANET_SECRET_KEY", "configured with non-default value"))

    if admin_password.lower() in DANGEROUS_SECRET_VALUES:
        level = "ERROR" if environment == "production" or non_localhost else "WARN"
        messages.append(CheckMessage(level, "INTRANET_ADMIN_PASSWORD", "empty or unsafe default admin password"))
    elif len(admin_password) < 10:
        level = "ERROR" if environment == "production" or non_localhost else "WARN"
        messages.append(CheckMessage(level, "INTRANET_ADMIN_PASSWORD", "admin password should be at least 10 characters"))
    else:
        messages.append(CheckMessage("OK", "INTRANET_ADMIN_PASSWORD", "configured with non-default value"))

    return messages


def _check_ai_configuration(environ: Mapping[str, str]) -> list[CheckMessage]:
    provider = _text(environ, "AI_PROVIDER", "bailian").lower()
    if provider in DISABLED_AI_PROVIDERS:
        return [CheckMessage("OK", "AI_PROVIDER", "AI provider is disabled")]
    if not _text(environ, "DASHSCOPE_API_KEY", ""):
        return [CheckMessage("WARN", "DASHSCOPE_API_KEY", "missing; AI features may be unavailable, but non-AI business flows can start")]
    return [CheckMessage("OK", "DASHSCOPE_API_KEY", "configured")]


def _merged_environ(env_file: Path, current_environ: Mapping[str, str]) -> dict[str, str]:
    merged = dict(current_environ)
    if env_file.exists():
        for key, value in _read_env_file(env_file).items():
            merged.setdefault(key, value)
    return merged


def _read_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        result[key] = _strip_quotes(value.strip())
    return result


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _text(environ: Mapping[str, str], name: str, default: str) -> str:
    value = environ.get(name, default)
    if value is None:
        return ""
    return str(value).strip()


def _path(environ: Mapping[str, str], name: str, default: Path) -> Path:
    value = _text(environ, name, "")
    if value:
        return Path(value)
    return default


def _is_writable_directory(path: Path) -> tuple[bool, str]:
    probe = path / ".preflight_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _print_result(result: PreflightResult) -> None:
    for item in result.messages:
        print(f"[{item.level}] {item.name}: {item.message}")
    if result.has_errors:
        print("Preflight failed.")
    elif result.has_warnings:
        print("Preflight passed with warnings.")
    else:
        print("Preflight passed.")


if __name__ == "__main__":
    raise SystemExit(main())