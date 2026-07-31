from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from intranet_app.domain import ValidationError
from intranet_app.io_utils import write_csv


@dataclass(frozen=True)
class ResultAsset:
    path: Path
    filename: str
    size: int

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("path must be pathlib.Path")
        if not isinstance(self.filename, str) or not self.filename.strip():
            raise ValueError("filename must not be empty")
        if not isinstance(self.size, int) or self.size < 0:
            raise ValueError("size must be non-negative int")

    def to_payload(self) -> dict[str, str | int]:
        payload: dict[str, str | int] = {
            "path": str(self.path),
            "file_path": str(self.path),
            "filename": self.filename,
            "size": self.size,
        }
        assert payload["filename"]
        return payload


class ResultAssetService:
    def __init__(self, base_dir: Path) -> None:
        if not isinstance(base_dir, Path):
            raise TypeError("base_dir must be pathlib.Path")
        self._base_dir = base_dir

    def save_csv(self, filename: str, rows: list[dict[str, str]]) -> ResultAsset:
        safe_name = _safe_filename(filename, ".csv")
        if not isinstance(rows, list):
            raise TypeError("rows must be list")
        if not rows:
            raise ValidationError("result rows must not be empty")
        path = self._base_dir / safe_name
        write_csv(path, rows)
        asset = _asset_from_path(path)
        logging.info("saved result asset: %s bytes=%s", asset.path, asset.size)
        assert asset.size > 0
        return asset

    def save_text(self, filename: str, content: str) -> ResultAsset:
        safe_name = _safe_filename(filename, ".txt")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must not be empty")
        path = self._base_dir / safe_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        asset = _asset_from_path(path)
        logging.info("saved text result asset: %s bytes=%s", asset.path, asset.size)
        assert asset.size > 0
        return asset

    def download_info(self, filename: str) -> ResultAsset:
        safe_name = _safe_filename(filename, "")
        path = self._base_dir / safe_name
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path))
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
