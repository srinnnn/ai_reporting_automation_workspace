from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.repositories.sqlite.feedback_repository import SQLiteFeedbackRepository
from intranet_app.storage import AppStorage


class SQLiteFeedbackRepositoryTests(unittest.TestCase):
    def test_missing_database_returns_empty_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository = SQLiteFeedbackRepository(Path(tmp_dir) / "missing.sqlite3")

            self.assertEqual(repository.list_feedback(), ())

    def test_existing_database_without_feedback_table_returns_empty_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_path = Path(tmp_dir) / "empty.sqlite3"
            sqlite3.connect(database_path).close()

            self.assertEqual(SQLiteFeedbackRepository(database_path).list_feedback(), ())

    def test_reads_existing_feedback_schema_and_multiple_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_path = Path(tmp_dir) / "runtime" / "test.sqlite3"
            storage = AppStorage(database_path)
            storage.initialize("test-password")
            storage.save_project_feedback("安踏周报/月报", "1小时", "反馈A", "迭代A", "tester-a", "2小时")
            storage.save_project_feedback("博西短彩信数据处理", "2小时", "反馈B", "迭代B", "tester-b", "4小时")

            records = SQLiteFeedbackRepository(database_path).list_feedback()

        self.assertEqual(len(records), 2)
        by_project = {record.project: record for record in records}
        self.assertEqual(by_project["安踏周报/月报"].original_manual_time, "2小时")
        self.assertEqual(by_project["安踏周报/月报"].current_processing_time, "1小时")
        self.assertEqual(by_project["博西短彩信数据处理"].business_feedback, "反馈B")
        self.assertEqual(by_project["博西短彩信数据处理"].iteration_need, "迭代B")
        self.assertEqual(by_project["博西短彩信数据处理"].updated_by, "tester-b")
        self.assertTrue(by_project["博西短彩信数据处理"].updated_at)

    def test_rejects_non_path_database(self) -> None:
        with self.assertRaisesRegex(TypeError, "pathlib.Path"):
            SQLiteFeedbackRepository("test.sqlite3")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
