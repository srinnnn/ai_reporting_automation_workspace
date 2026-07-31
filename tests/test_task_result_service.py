from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.repositories.interfaces import AutomationTaskCreate, TaskRepository, TaskRunCreate
from backend.services.task_query_service import TaskQueryService, TaskReadModel
from backend.services.task_result_service import TaskResultService
from intranet_app.storage import AutomationRunRecord, AutomationTaskRecord


class TaskResultServiceTests(unittest.TestCase):
    def test_success_task_returns_safe_result_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = _write_asset(Path(temp_dir), "daily.csv")
            service = _service(asset_path, Path(temp_dir))

            result = service.get_result(1)

            self.assertEqual(result.task_id, 1)
            self.assertEqual(result.status, "success")
            self.assertEqual(result.filename, "daily.csv")
            self.assertEqual(result.file_path, "task-results/1/daily.csv")
            self.assertNotIn(str(Path(temp_dir)), result.file_path)
            self.assertEqual(result.result_asset["filename"], "daily.csv")

    def test_missing_file_is_not_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.csv"
            service = _service(missing_path, Path(temp_dir))

            with self.assertRaises(FileNotFoundError):
                service.get_result(1)

    def test_failed_task_has_no_download_info(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = _write_asset(Path(temp_dir), "daily.csv")
            service = _service(asset_path, Path(temp_dir))

            with self.assertRaisesRegex(ValueError, "successful"):
                service.get_download_info(2)

    def test_download_info_returns_backend_path_for_success_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = _write_asset(Path(temp_dir), "daily.csv")
            service = _service(asset_path, Path(temp_dir))

            info = service.get_download_info(1)

            self.assertEqual(info.filename, "daily.csv")
            self.assertEqual(info.path, asset_path.resolve())

    def test_new_read_model_result_asset_has_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            new_path = _write_asset(root, "new-daily.csv")
            legacy_path = _write_asset(root, "legacy-daily.csv")
            service = TaskResultService(
                _StaticTaskQueryService(
                    _read_model(
                        result={"result_asset": {"file_path": str(legacy_path), "filename": legacy_path.name, "size": 21}},
                        result_asset={"file_path": str(new_path), "filename": new_path.name, "size": 20},
                    )
                ),
                root,
            )

            result = service.get_result(1)

            self.assertEqual(result.filename, "new-daily.csv")
            self.assertEqual(result.file_path, "task-results/1/new-daily.csv")

    def test_legacy_result_asset_format_still_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy_path = _write_asset(root, "legacy-daily.csv")
            service = TaskResultService(
                _StaticTaskQueryService(
                    _read_model(
                        result={"result_asset": {"file_path": str(legacy_path), "filename": legacy_path.name, "size": 21}},
                        result_asset=None,
                    )
                ),
                root,
            )

            info = service.get_download_info(1)

            self.assertEqual(info.filename, "legacy-daily.csv")
            self.assertEqual(info.path, legacy_path.resolve())

    def test_success_task_without_result_asset_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = TaskResultService(_StaticTaskQueryService(_read_model(result={}, result_asset=None)), Path(temp_dir))

            with self.assertRaisesRegex(FileNotFoundError, "result asset missing"):
                service.get_result(1)


def _service(asset_path: Path, allowed_root: Path) -> TaskResultService:
    return TaskResultService(TaskQueryService(_TaskRepository(asset_path)), allowed_root)


def _write_asset(root: Path, filename: str) -> Path:
    path = root / filename
    path.write_text("metric,value\nsales,100\n", encoding="utf-8")
    return path


class _TaskRepository(TaskRepository):
    def __init__(self, asset_path: Path) -> None:
        self._asset_path = asset_path

    def create_task(self, request: AutomationTaskCreate) -> int:
        raise NotImplementedError

    def update_task_status(self, task_id: int, status: str) -> None:
        raise NotImplementedError

    def get_task(self, task_id: int) -> AutomationTaskRecord | None:
        for task in self.list_tasks():
            if task.id == task_id:
                return task
        return None

    def save_task_result(self, request: TaskRunCreate) -> int:
        raise NotImplementedError

    def list_tasks(self) -> list[AutomationTaskRecord]:
        return [
            _task(1, "REPORT_GENERATE"),
            _task(2, "REPORT_GENERATE"),
        ]

    def list_task_runs(self, limit: int = 200) -> list[AutomationRunRecord]:
        return [
            _run(10, 2, "failed", "error: foundation data missing"),
            _run(
                9,
                1,
                "success",
                json.dumps(
                    {
                        "result_asset": {
                            "file_path": str(self._asset_path),
                            "filename": self._asset_path.name,
                            "size": 21,
                        }
                    },
                    ensure_ascii=False,
                ),
            ),
        ]


class _StaticTaskQueryService(TaskQueryService):
    def __init__(self, task: TaskReadModel) -> None:
        self._task = task

    def get_task(self, task_id: int) -> TaskReadModel | None:
        if task_id == self._task.task_id:
            return self._task
        return None


def _read_model(
    result: dict[str, object],
    result_asset: dict[str, object] | None,
    status: str = "success",
) -> TaskReadModel:
    return TaskReadModel(
        task_id=1,
        task_type="REPORT_GENERATE",
        status=status,
        created_by="admin",
        created_time="2026-07-30T17:45:00+08:00",
        result=result,
        error="",
        owner="admin",
        brand_id="anta_kids",
        business_unit="anta_retail_team",
        platform="meituan",
        channel="instant_retail",
        updated_at="2026-07-30T17:46:00+08:00",
        scope_snapshot={"brand_id": "anta_kids"},
        result_asset=result_asset,
    )


def _task(task_id: int, task_type: str) -> AutomationTaskRecord:
    return AutomationTaskRecord(
        id=task_id,
        task_name=f"task-{task_id}",
        business_unit="anta_retail_team",
        brand_id="anta_kids",
        brand_name="Anta Kids",
        platform="meituan",
        channel="instant_retail",
        file_type=task_type,
        frequency="daily",
        scheduled_time="09:30",
        date_window="20260725",
        enabled=True,
        output_folder="runtime/results",
        owner="admin",
        notes="",
        created_at="2026-07-30T17:45:00+08:00",
        updated_at="2026-07-30T17:45:00+08:00",
    )


def _run(run_id: int, task_id: int, status: str, message: str) -> AutomationRunRecord:
    return AutomationRunRecord(
        id=run_id,
        task_id=task_id,
        task_name=f"task-{task_id}",
        run_date="20260725",
        status=status,
        downloaded_file_count=0,
        synced_file_count=0,
        message=message,
        executed_by="admin",
        created_at="2026-07-30T17:46:00+08:00",
    )


if __name__ == "__main__":
    unittest.main()
