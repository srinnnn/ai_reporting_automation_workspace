from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.core.config import CoreConfig
from backend.core.container import ApplicationContainer
from backend.core.health import check_system_health
from backend.services.permission_service import PermissionService
from intranet_app.storage import UserRecord


@dataclass(frozen=True)
class SystemStatusService:
    container: ApplicationContainer
    permissions: PermissionService

    def __post_init__(self) -> None:
        if not isinstance(self.container, ApplicationContainer):
            raise TypeError("container must be ApplicationContainer")
        if not isinstance(self.permissions, PermissionService):
            raise TypeError("permissions must be PermissionService")

    def get_health_status(self, user: UserRecord) -> dict[str, object]:
        self._require_system_access(user)
        health = check_system_health(self.container.config)
        result = health.to_dict()
        assert "components" in result
        return result

    def get_config_status(self, user: UserRecord) -> dict[str, object]:
        self._require_system_access(user)
        config = self.container.config
        result = {
            "app_env": config.environment,
            "database_backend": config.database.backend,
            "report_task_mode": config.report_task_mode,
            "ai_provider": config.ai.provider,
            "ai_model": config.ai.model,
            "ai_api_key_configured": config.ai.api_key_configured,
            "storage": _storage_status(config),
        }
        assert "ai_api_key_configured" in result
        return result

    def _require_system_access(self, user: UserRecord) -> None:
        if not isinstance(user, UserRecord):
            raise TypeError("user must be UserRecord")
        if _role_key(user.role) not in {"admin", "developer"}:
            raise PermissionError("forbidden")


def _storage_status(config: CoreConfig) -> dict[str, object]:
    if not isinstance(config, CoreConfig):
        raise TypeError("config must be CoreConfig")
    result = {
        "runtime_dir": _path_status(config.files.runtime_dir),
        "upload_dir": _path_status(config.files.upload_dir),
        "result_dir": _path_status(config.files.result_dir),
        "log_dir": _path_status(config.files.log_dir),
        "provider": "local",
    }
    assert result["provider"] == "local"
    return result


def _path_status(path: Path) -> dict[str, bool]:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    result = {
        "configured": True,
        "exists": path.exists(),
        "writable": path.exists() and path.is_dir() and _is_writable(path),
    }
    assert isinstance(result["exists"], bool)
    return result


def _is_writable(path: Path) -> bool:
    probe = path / ".system_status_write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def _role_key(role: str) -> str:
    if not isinstance(role, str):
        raise TypeError("role must be str")
    text = role.strip().lower()
    if not text:
        raise ValueError("role must not be empty")
    if any(marker in text for marker in ("admin", "administrator", "管理员", "系统管理员")):
        return "admin"
    if any(marker in text for marker in ("developer", "dev", "开发", "开发者", "运维")):
        return "developer"
    if any(marker in text for marker in ("business_owner", "business owner", "owner", "业务负责人", "负责人")):
        return "business_owner"
    if any(marker in text for marker in ("viewer", "read_only", "readonly", "查看者", "只读", "访客")):
        return "viewer"
    return "user"