"""Backward-compatible import path for result asset persistence.

New code should import from backend.services.assets.asset_service and pass an explicit
StorageProvider. This module remains so existing tests and legacy callers that construct
ResultAssetService(Path(...)) continue to work while storage.py is frozen as legacy.
"""

from __future__ import annotations

from pathlib import Path

from backend.services.assets.asset_service import ResultAsset, ResultAssetService as _ResultAssetService, StorageProvider
from backend.services.assets.providers.local_provider import LocalStorageProvider


class ResultAssetService(_ResultAssetService):
    def __init__(self, base_dir_or_provider: Path | StorageProvider) -> None:
        if isinstance(base_dir_or_provider, Path):
            provider = LocalStorageProvider(base_dir_or_provider)
        elif isinstance(base_dir_or_provider, StorageProvider):
            provider = base_dir_or_provider
        else:
            raise TypeError("base_dir_or_provider must be pathlib.Path or StorageProvider")
        super().__init__(provider)


__all__ = ["LocalStorageProvider", "ResultAsset", "ResultAssetService", "StorageProvider"]
