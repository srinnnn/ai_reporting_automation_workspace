from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.task_query_service import TaskQueryService, TaskReadModel


@dataclass(frozen=True)
class TaskResultView:
    task_id: int
    status: str
    result_asset: dict[str, str | int]
    filename: str
    file_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, int) or self.task_id <= 0:
            raise ValueError("task_id must be positive int")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must not be empty")
        if not isinstance(self.result_asset, dict):
            raise TypeError("result_asset must be dict")
        if not isinstance(self.filename, str) or not self.filename.strip():
            raise ValueError("filename must not be empty")
        if not isinstance(self.file_path, str) or not self.file_path.strip():
            raise ValueError("file_path must not be empty")

    def to_payload(self) -> dict[str, object]:
        payload = {
            "task_id": self.task_id,
            "status": self.status,
            "result_asset": self.result_asset,
            "filename": self.filename,
            "file_path": self.file_path,
        }
        assert payload["task_id"] == self.task_id
        return payload


@dataclass(frozen=True)
class TaskDownloadInfo:
    filename: str
    path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.filename, str) or not self.filename.strip():
            raise ValueError("filename must not be empty")
        if not isinstance(self.path, Path):
            raise TypeError("path must be pathlib.Path")
        if not self.path.exists() or not self.path.is_file():
            raise FileNotFoundError(str(self.path))


class TaskResultService:
    def __init__(self, task_query_service: TaskQueryService, allowed_result_root: Path | None = None) -> None:
        if not isinstance(task_query_service, TaskQueryService):
            raise TypeError("task_query_service must be TaskQueryService")
        if allowed_result_root is not None and not isinstance(allowed_result_root, Path):
            raise TypeError("allowed_result_root must be pathlib.Path")
        self._task_query_service = task_query_service
        self._allowed_result_root = allowed_result_root.resolve() if allowed_result_root is not None else None

    def get_result(self, task_id: int) -> TaskResultView:
        task = self._get_existing_task(task_id)
        asset = _result_asset_from_task(task)
        filename = _filename_from_asset(asset)
        path = self._validated_asset_path(asset)
        safe_asset: dict[str, str | int] = {
            "filename": filename,
            "size": _asset_size(asset, path),
        }
        view = TaskResultView(
            task_id=task.task_id,
            status=task.status,
            result_asset=safe_asset,
            filename=filename,
            file_path=_public_result_path(task.task_id, filename),
        )
        assert view.filename == filename
        return view

    def get_download_info(self, task_id: int) -> TaskDownloadInfo:
        task = self._get_existing_task(task_id)
        if task.status != "success":
            raise ValueError("only successful tasks can be downloaded")
        asset = _result_asset_from_task(task)
        path = self._validated_asset_path(asset)
        filename = _filename_from_asset(asset)
        info = TaskDownloadInfo(filename=filename, path=path)
        assert info.path.exists()
        return info

    def _get_existing_task(self, task_id: int) -> TaskReadModel:
        if not isinstance(task_id, int) or task_id <= 0:
            raise ValueError("task_id must be positive int")
        task = self._task_query_service.get_task(task_id)
        if task is None:
            raise FileNotFoundError(f"task not found: {task_id}")
        assert isinstance(task, TaskReadModel)
        return task

    def _validated_asset_path(self, asset: dict[str, Any]) -> Path:
        raw_path = asset.get("file_path") or asset.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise FileNotFoundError("result asset path missing")
        path = Path(raw_path.strip()).resolve()
        if self._allowed_result_root is not None and not _is_relative_to(path, self._allowed_result_root):
            raise PermissionError("result asset path is outside allowed result root")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path))
        return path


def _result_asset_from_task(task: TaskReadModel) -> dict[str, Any]:
    if not isinstance(task, TaskReadModel):
        raise TypeError("task must be TaskReadModel")
    if task.status != "success":
        raise ValueError("task result is not downloadable unless status is success")
    asset = task.result_asset
    if asset is None:
        asset = task.result.get("result_asset")
    if not isinstance(asset, dict):
        raise FileNotFoundError("result asset missing")
    result = dict(asset)
    assert isinstance(result, dict)
    return result


def _filename_from_asset(asset: dict[str, Any]) -> str:
    filename = asset.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        raise FileNotFoundError("result asset filename missing")
    result = Path(filename.strip()).name
    if result != filename.strip() or result in {"", ".", ".."}:
        raise ValueError("result asset filename is not safe")
    assert result
    return result


def _asset_size(asset: dict[str, Any], path: Path) -> int:
    size = asset.get("size")
    if isinstance(size, int) and size >= 0:
        return size
    actual_size = path.stat().st_size
    assert actual_size >= 0
    return actual_size


def _public_result_path(task_id: int, filename: str) -> str:
    if not isinstance(task_id, int) or task_id <= 0:
        raise ValueError("task_id must be positive int")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must not be empty")
    result = f"task-results/{task_id}/{filename}"
    assert result
    return result


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
