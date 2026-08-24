from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class FastApiAppTests(unittest.TestCase):
    def test_health_ready_version_and_production_empty_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch.dict(
                "os.environ",
                {
                    "APP_ENV": "testing",
                    "DEMO_MODE": "false",
                    "RUNTIME_DIR": str(root / "runtime"),
                    "SQLITE_PATH": str(root / "runtime" / "intranet.sqlite3"),
                    "APP_COMMIT_SHA": "test-sha",
                    "APP_BUILD_TIME": "2026-08-24T00:00:00Z",
                },
                clear=False,
            ):
                from backend.main import create_app

                client = TestClient(create_app())
                self.assertEqual(client.get("/api/v1/health").json(), {"status": "ok"})
                self.assertEqual(client.get("/api/v1/ready").json()["status"], "ok")
                self.assertEqual(client.get("/api/v1/version").json()["commit_sha"], "test-sha")
                dashboard = client.get("/api/v1/dashboard").json()

        self.assertEqual(dashboard["kpis"]["brand_count"], 0)
        self.assertEqual(dashboard["brands"], [])
        self.assertNotIn("AI选品辅助", str(dashboard))
        self.assertNotIn("文案内容辅助", str(dashboard))

    def test_demo_mode_exposes_demo_brand_without_changing_production_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch.dict("os.environ", {"APP_ENV": "testing", "DEMO_MODE": "true", "RUNTIME_DIR": str(root / "runtime")}, clear=False):
                from backend.main import create_app

                client = TestClient(create_app())
                brand = client.get("/api/v1/brands/ANTA").json()

        self.assertEqual(brand["active_category_count"], 2)

    def test_unknown_brand_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch.dict("os.environ", {"APP_ENV": "testing", "DEMO_MODE": "false", "RUNTIME_DIR": str(root / "runtime")}, clear=False):
                from backend.main import create_app

                client = TestClient(create_app())
                response = client.get("/api/v1/brands/UNKNOWN")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
