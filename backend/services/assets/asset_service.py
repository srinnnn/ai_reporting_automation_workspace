"""Result asset service boundary.

This module owns result asset orchestration only. Concrete persistence is delegated to a
StorageProvider so executors do not know local runtime paths or future OSS/S3 details.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from intranet_app.domain import ValidationError


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


class StorageProvider(ABC):
    @abstractmethod
    def save_csv(self, filename: str, rows: list[dict[str, str]]) -> ResultAsset:
        raise NotImplementedError

    @abstractmethod
    def save_text(self, filename: str, content: str) -> ResultAsset:
        raise NotImplementedError

    @abstractmethod
    def get_asset(self, filename: str) -> ResultAsset:
        raise NotImplementedError


class ResultAssetService:
    def __init__(self, storage_provider: StorageProvider) -> None:
        if not isinstance(storage_provider, StorageProvider):
            raise TypeError("storage_provider must be StorageProvider")
        self._storage_provider = storage_provider

    def save_csv(self, filename: str, rows: list[dict[str, str]]) -> ResultAsset:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename must not be empty")
        if not isinstance(rows, list):
            raise TypeError("rows must be list")
        if not rows:
            raise ValidationError("result rows must not be empty")
        asset = self._storage_provider.save_csv(filename, rows)
        logging.info("saved result asset: %s bytes=%s", asset.path, asset.size)
        assert asset.size > 0
        return asset

    def save_text(self, filename: str, content: str) -> ResultAsset:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename must not be empty")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must not be empty")
        asset = self._storage_provider.save_text(filename, content)
        logging.info("saved text result asset: %s bytes=%s", asset.path, asset.size)
        assert asset.size > 0
        return asset

    def download_info(self, filename: str) -> ResultAsset:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename must not be empty")
        asset = self._storage_provider.get_asset(filename)
        assert asset.filename
        return asset
