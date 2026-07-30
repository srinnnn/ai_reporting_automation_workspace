from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intranet_app.storage import AppStorage


class ProjectFeedbackStorageTests(unittest.TestCase):
    def test_save_and_update_project_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            first = storage.save_project_feedback("安踏周报/月报", "8分钟/次", "操作顺畅", "增加PPT导出", "business_a", "25小时/月")
            second = storage.save_project_feedback("安踏周报/月报", "5分钟/次", "需要提速", "增加日报", "business_b", "20小时/月")
            records = storage.list_project_feedback()

            self.assertEqual(first.project, "安踏周报/月报")
            self.assertEqual(first.original_manual_time, "25小时")
            self.assertEqual(len(records), 1)
            self.assertEqual(records["安踏周报/月报"].business_feedback, "需要提速")
            self.assertEqual(records["安踏周报/月报"].original_manual_time, "20小时")
            self.assertEqual(records["安踏周报/月报"].current_processing_time, "0.08小时")
            self.assertEqual(records["安踏周报/月报"].iteration_need, "增加日报")
            self.assertEqual(second.updated_by, "business_b")

    def test_save_allows_empty_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            record = storage.save_project_feedback("页面巡检复盘", "", "", "", "admin")
            self.assertEqual(record.original_manual_time, "")
            self.assertEqual(record.current_processing_time, "")
            self.assertEqual(record.business_feedback, "")
            self.assertEqual(record.iteration_need, "")

    def test_save_rejects_excessive_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            with self.assertRaisesRegex(ValueError, "2000"):
                storage.save_project_feedback("AI选品辅助", "", "x" * 2001, "", "admin")

    def test_save_rejects_excessive_processing_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            with self.assertRaisesRegex(ValueError, "100"):
                storage.save_project_feedback("AI选品辅助", "x" * 101, "", "", "admin")

    def test_save_rejects_excessive_original_manual_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            with self.assertRaisesRegex(ValueError, "100"):
                storage.save_project_feedback("AI选品辅助", "", "", "", "admin", "x" * 101)

    def test_save_normalizes_hour_based_processing_time_to_minutes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            record = storage.save_project_feedback("AI选品辅助", "40分钟", "", "", "admin", "120分钟")
            self.assertEqual(record.current_processing_time, "0.67小时")
            self.assertEqual(record.original_manual_time, "2小时")

    def test_save_and_list_efficiency_mapping_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            record = storage.save_efficiency_mapping_note(
                task_name="日报（日常销售报数）",
                brand_name="CK",
                not_improved_reason="缺少稳定日报源文件",
                schedule_plan="第2周确认字段，第3周接入",
                updated_by="admin",
            )
            records = storage.list_efficiency_mapping_notes()

            self.assertEqual(record.task_name, "日报（日常销售报数）")
            self.assertIn(("日报（日常销售报数）", "CK"), records)
            self.assertEqual(records[("日报（日常销售报数）", "CK")].not_improved_reason, "缺少稳定日报源文件")
            self.assertEqual(records[("日报（日常销售报数）", "CK")].schedule_plan, "第2周确认字段，第3周接入")
            self.assertFalse(records[("日报（日常销售报数）", "CK")].is_improved)
            self.assertFalse(records[("日报（日常销售报数）", "CK")].is_manual_brand)

    def test_save_efficiency_mapping_note_supports_manual_improved_brand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            storage.save_efficiency_mapping_note(
                task_name="周报（周数据整合）",
                brand_name="新品牌",
                not_improved_reason="",
                schedule_plan="第4周接入",
                updated_by="admin",
                is_improved=True,
                is_manual_brand=True,
            )
            records = storage.list_efficiency_mapping_notes()

            record = records[("周报（周数据整合）", "新品牌")]
            self.assertTrue(record.is_improved)
            self.assertTrue(record.is_manual_brand)

    def test_save_efficiency_mapping_note_rejects_empty_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            with self.assertRaisesRegex(ValueError, "task_name"):
                storage.save_efficiency_mapping_note("", "CK", "", "", "admin")

    def test_save_efficiency_mapping_note_rejects_excessive_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = _storage(Path(tmp_dir))
            with self.assertRaisesRegex(ValueError, "2000"):
                storage.save_efficiency_mapping_note("日报（日常销售报数）", "CK", "x" * 2001, "", "admin")


def _storage(root: Path) -> AppStorage:
    storage = AppStorage(root / "runtime" / "test.sqlite3")
    storage.initialize("test-password")
    return storage


if __name__ == "__main__":
    unittest.main()
