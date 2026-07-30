from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.config import AppConfig
from intranet_app.storage import AppStorage, UserRecord


class AutomationRunStorageTests(unittest.TestCase):
    def test_initialize_creates_default_anta_meituan_daily_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))

            tasks = storage.list_automation_tasks()

            self.assertEqual(len(tasks), 3)
            self.assertEqual({task.frequency for task in tasks}, {"daily"})
            self.assertEqual({task.brand_id for task in tasks}, {"anta_kids"})
            self.assertEqual(
                {task.file_type for task in tasks},
                {"product_order", "store_finance", "store_traffic"},
            )

    def test_initialize_removes_legacy_daily_service_review_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage = _storage(root)
            storage.save_automation_task(
                task_name="安踏美团日报-服务评价",
                business_unit="anta_retail_team",
                brand_id="anta_kids",
                brand_name="安踏儿童",
                platform="meituan",
                channel="instant_retail",
                file_type="service_review",
                frequency="daily",
                scheduled_time="09:45",
                date_window="yesterday",
                enabled=True,
                output_folder="meituan_auto_download/anta_kids/instant_retail",
                owner="business",
                notes="旧日报默认任务。",
            )

            storage.initialize("test-password")
            tasks = storage.list_automation_tasks()

            self.assertNotIn("安踏美团日报-服务评价", {task.task_name for task in tasks})

    def test_save_task_toggle_and_run_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            task_id = storage.save_automation_task(
                task_name="京东日报-商品订单",
                business_unit="anta_retail_team",
                brand_id="anta_kids",
                brand_name="安踏儿童",
                platform="jd",
                channel="ecommerce",
                file_type="product_order",
                frequency="daily",
                scheduled_time="10:00",
                date_window="yesterday",
                enabled=True,
                output_folder="jd_auto_download/anta_kids/ecommerce",
                owner="business",
                notes="用于后续多渠道统一入库。",
            )

            storage.set_automation_task_enabled(task_id, False)
            storage.save_automation_run(
                task_id=task_id,
                run_date="2026-07-27",
                status="manual_done",
                downloaded_file_count=1,
                synced_file_count=0,
                message="已下载，待同步。",
                executed_by="admin",
            )

            task = storage.get_automation_task(task_id)
            runs = storage.list_automation_runs()
            self.assertIsNotNone(task)
            self.assertFalse(task.enabled)
            self.assertEqual(runs[0].task_name, "京东日报-商品订单")
            self.assertEqual(runs[0].downloaded_file_count, 1)


class AutomationRunPageTests(unittest.TestCase):
    def test_page_and_dashboard_expose_automation_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            app.initialize()
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            dashboard = app._dashboard(user)
            page = app._automation_runs_page(user, "", "")

            self.assertIn('href="/automation-runs"', dashboard)
            self.assertIn("自动化数据执行", page)
            self.assertIn("每日任务计划", page)
            self.assertIn("安踏美团日报-商品订单", page)
            self.assertIn('action="/automation-runs/execute"', page)
            self.assertIn("执行同步、入库与校验", page)
            self.assertIn("仅同步浏览器下载目录", page)

    def test_automation_status_labels_include_real_execution_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))

            self.assertEqual(app._automation_status_label("foundation_ready"), "基础层就绪")
            self.assertEqual(app._automation_status_label("missing_source"), "缺少源数据")


def _storage(root: Path) -> AppStorage:
    storage = AppStorage(root / "runtime" / "test.sqlite3")
    storage.initialize("test-password")
    return storage


def _config(root: Path) -> AppConfig:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    return AppConfig(
        host="127.0.0.1",
        port=8765,
        secret_key="test-secret",
        database_path=root / "runtime" / "intranet.sqlite3",
        upload_dir=root / "runtime" / "uploads",
        result_dir=root / "runtime" / "results",
        template_root=root / "materials",
        default_admin_password="admin123",
    )


if __name__ == "__main__":
    unittest.main()
