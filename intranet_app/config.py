from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    secret_key: str
    database_path: Path
    upload_dir: Path
    result_dir: Path
    template_root: Path
    default_admin_password: str

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("host must not be empty")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if not self.secret_key.strip():
            raise ValueError("secret_key must not be empty")
        if not self.default_admin_password.strip():
            raise ValueError("default_admin_password must not be empty")
        if self.host not in ("127.0.0.1", "localhost", "::1") and self.default_admin_password == "admin123":
            raise ValueError("局域网模式不能使用默认密码 admin123，请设置正式管理员密码")
        if self.host not in ("127.0.0.1", "localhost", "::1") and len(self.default_admin_password) < 10:
            raise ValueError("局域网模式管理员密码至少需要10位")
        for path_value in (self.database_path, self.upload_dir, self.result_dir, self.template_root):
            if not isinstance(path_value, Path):
                raise TypeError("all path values must be pathlib.Path")


ROOT_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT_DIR / "intranet_app" / "runtime"

DEFAULT_CONFIG = AppConfig(
    host=os.environ.get("INTRANET_HOST", "127.0.0.1"),
    port=int(os.environ.get("INTRANET_PORT", "8785")),
    secret_key=os.environ.get("INTRANET_SECRET_KEY", "change-this-before-shared-intranet-use"),
    database_path=RUNTIME_DIR / "intranet.sqlite3",
    upload_dir=RUNTIME_DIR / "uploads",
    result_dir=RUNTIME_DIR / "results",
    template_root=ROOT_DIR / "ai_report_config_materials",
    default_admin_password=os.environ.get("INTRANET_ADMIN_PASSWORD", "admin123"),
)
