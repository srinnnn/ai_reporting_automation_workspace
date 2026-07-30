from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROJECT_ROOT = Path(r"C:\Users\JM042403\Documents\安踏即时零售（上下架筛选+选品）")


@dataclass(frozen=True)
class AntaRetailLaunchConfig:
    host: str
    port: int
    project_root: Path

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("host must be a non-empty string")
        if not isinstance(self.port, int) or self.port <= 0 or self.port > 65535:
            raise ValueError("port must be between 1 and 65535")
        if not isinstance(self.project_root, Path):
            raise TypeError("project_root must be pathlib.Path")
        if not self.project_root.exists():
            raise ValueError(f"安踏即时零售项目目录不存在：{self.project_root}")
        if not (self.project_root / "src" / "anta_listing_checker" / "local_ui.py").exists():
            raise ValueError(f"安踏即时零售网页入口不存在：{self.project_root}")


def load_config_from_env() -> AntaRetailLaunchConfig:
    host = os.environ.get("ANTA_RETAIL_HOST", "127.0.0.1").strip() or "127.0.0.1"
    raw_port = os.environ.get("ANTA_RETAIL_PORT", "8766").strip() or "8766"
    raw_root = os.environ.get("ANTA_RETAIL_PROJECT_ROOT", str(DEFAULT_PROJECT_ROOT)).strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("ANTA_RETAIL_PORT must be an integer") from exc
    config = AntaRetailLaunchConfig(host=host, port=port, project_root=Path(raw_root))
    assert isinstance(config, AntaRetailLaunchConfig)
    return config


def run_anta_retail_server(config: AntaRetailLaunchConfig) -> None:
    if not isinstance(config, AntaRetailLaunchConfig):
        raise TypeError("config must be AntaRetailLaunchConfig")
    src_dir = config.project_root / "src"
    sys.path.insert(0, str(src_dir))
    from anta_listing_checker.local_ui import LocalUiConfig, run_server

    logging.info("starting anta retail web: http://%s:%s", config.host, config.port)
    run_server(LocalUiConfig(host=config.host, port=config.port, project_root=config.project_root))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config_from_env()
    run_anta_retail_server(config)


if __name__ == "__main__":
    main()
