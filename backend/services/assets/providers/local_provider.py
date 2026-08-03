from __future__ import annotations

import re
from pathlib import Path

from backend.services.assets.asset_service import ResultAsset, StorageProvider
from intranet_app.io_utils import write_csv


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: Path) -> None:
        if not isinstance(base_dir, Path):
            raise TypeError("base_dir must be pathlib.Path")
        self._base_dir = base_dir

    def save_csv(self, filename: str, rows: list[dict[str, str]]) -> ResultAsset:
        safe_name = _safe_filename(filename, ".csv")
        path = self._base_dir / safe_name
        write_csv(path, rows)
        asset = _asset_from_path(path)
        assert asset.size > 0
        return asset

    def save_text(self, filename: str, content: str) -> ResultAsset:
        safe_name = _safe_filename(filename, ".txt")
        path = self._base_dir / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        asset = _asset_from_path(path)
        assert asset.size > 0
        return asset

    def get_asset(self, filename: str) -> ResultAsset:
        safe_name = _safe_filename(filename, "")
        path = self._base_dir / safe_name
        asset = _asset_from_path(path)
        assert asset.filename == safe_name
        return asset


def _asset_from_path(path: Path) -> ResultAsset:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    asset = ResultAsset(path=path.resolve(), filename=path.name, size=path.stat().st_size)
    assert asset.size >= 0
    return asset


def _safe_filename(filename: str, default_suffix: str) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must not be empty")
    name = Path(filename.strip()).name
    if not name or name in {".", ".."}:
        raise ValueError("filename must not be empty")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not cleaned:
        raise ValueError("filename must contain safe characters")
    if default_suffix and not cleaned.lower().endswith(default_suffix):
        cleaned = f"{cleaned}{default_suffix}"
    assert cleaned
    return cleaned
