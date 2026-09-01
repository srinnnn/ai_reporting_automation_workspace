from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from intranet_app.storage import AppStorage


class FeedbackApiTests(unittest.TestCase):
    def test_all_and_brand_filters_return_existing_feedback_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            database_path = root / "runtime" / "intranet.sqlite3"
            storage = AppStorage(database_path)
            storage.initialize("test-password")
            storage.save_project_feedback("P3-即时零售-安踏", "1小时", "ANTA feedback", "ANTA iteration", "tester", "2小时")
            storage.save_project_feedback("P3-活动机制配置-ECCO", "1小时", "ECCO feedback", "ECCO iteration", "tester", "2小时")
            storage.save_project_feedback("博西短彩信数据处理", "1小时", "BSH feedback", "BSH iteration", "tester", "2小时")
            storage.save_project_feedback("P1-短彩信数据处理-CK", "1小时", "Unmapped feedback", "Unmapped iteration", "tester", "2小时")
            with patch.dict(
                "os.environ",
                {
                    "APP_ENV": "testing",
                    "DEMO_MODE": "false",
                    "RUNTIME_DIR": str(root / "runtime"),
                    "SQLITE_PATH": str(database_path),
                },
                clear=False,
            ):
                from backend.main import create_app

                client = TestClient(create_app())
                all_records = client.get("/api/v1/feedback")
                anta = client.get("/api/v1/feedback", params={"brand": "ANTA"})
                ecco = client.get("/api/v1/feedback", params={"brand": "ECCO"})
                bsh = client.get("/api/v1/feedback", params={"brand": "BSH"})

        self.assertEqual(all_records.status_code, 200)
        self.assertEqual(len(all_records.json()), 4)
        self.assertEqual([record["project"] for record in anta.json()], ["P3-即时零售-安踏"])
        self.assertEqual([record["project"] for record in ecco.json()], ["P3-活动机制配置-ECCO"])
        self.assertEqual([record["project"] for record in bsh.json()], ["博西短彩信数据处理"])
        self.assertEqual(next(record for record in all_records.json() if record["status"] == "UNMAPPED")["project"], "P1-短彩信数据处理-CK")

    def test_invalid_category_returns_422(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            database_path = root / "runtime" / "intranet.sqlite3"
            storage = AppStorage(database_path)
            storage.initialize("test-password")
            with patch.dict("os.environ", {"APP_ENV": "testing", "SQLITE_PATH": str(database_path)}, clear=False):
                from backend.main import create_app

                response = TestClient(create_app()).get("/api/v1/feedback", params={"category": "P5"})

        self.assertEqual(response.status_code, 422)
        self.assertIn("P1-P4", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
