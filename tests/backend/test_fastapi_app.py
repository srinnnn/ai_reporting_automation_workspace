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

        self.assertEqual(dashboard["kpis"]["brand_count"], 3)
        self.assertEqual([brand["key"] for brand in dashboard["brands"]], ["ANTA", "ECCO", "BSH"])
        self.assertIn("安踏周报/月报", str(dashboard))
        self.assertNotIn("AI选品辅助", str(dashboard))
        self.assertNotIn("文案内容辅助", str(dashboard))

    def test_workspace_metadata_uses_existing_scenario_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch.dict("os.environ", {"APP_ENV": "testing", "DEMO_MODE": "false", "RUNTIME_DIR": str(root / "runtime")}, clear=False):
                from backend.main import create_app

                client = TestClient(create_app())
                brand = client.get("/api/v1/brands/ANTA").json()

        self.assertEqual(brand["active_category_count"], 2)
        categories = {category["key"]: category for category in brand["categories"]}
        self.assertEqual(
            [item["name"] for item in categories["P1"]["capabilities"]],
            ["安踏周报/月报", "私域数据采集中心"],
        )
        self.assertEqual(categories["P2"]["capabilities"], [])
        self.assertEqual([item["name"] for item in categories["P3"]["capabilities"]], ["安踏即时零售"])

    def test_ready_returns_503_when_production_frontend_dist_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch.dict(
                "os.environ",
                {
                    "APP_ENV": "production",
                    "DEMO_MODE": "false",
                    "RUNTIME_DIR": str(root / "runtime"),
                    "SQLITE_PATH": str(root / "runtime" / "intranet.sqlite3"),
                },
                clear=False,
            ):
                from backend.main import create_app

                with patch("backend.main.FRONTEND_DIST", root / "missing-dist"):
                    client = TestClient(create_app())
                    response = client.get("/api/v1/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["status"], "error")
        self.assertFalse(response.json()["detail"]["frontend_dist"])

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
