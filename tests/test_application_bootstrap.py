from __future__ import annotations

import tempfile
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from backend.core.container import ApplicationContainer, build_application_container
from intranet_app.app import IntranetApp, create_intranet_app
from intranet_app.config import AppConfig


class ApplicationBootstrapTests(unittest.TestCase):
    def test_create_intranet_app_attaches_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            container = build_application_container(environ=_env(root), root_dir=root)
            app = create_intranet_app(_config(root), container)
            try:
                self.assertIs(app.container, container)
                self.assertIsInstance(app.container, ApplicationContainer)
                self.assertIsNotNone(app.storage)
            finally:
                app.close()

    def test_create_intranet_app_can_build_container_from_app_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = create_intranet_app(_config(root))
            try:
                self.assertIsInstance(app.container, ApplicationContainer)
                self.assertEqual(app.container.config.database.sqlite_path, _config(root).database_path)
                self.assertEqual(app.container.config.files.result_dir, _config(root).result_dir)
            finally:
                app.close()
    def test_legacy_constructor_still_initializes_without_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = IntranetApp(_config(root))

            app.initialize()

            self.assertIsNone(app.container)
            self.assertTrue((_config(root).database_path).exists())

    def test_legacy_handler_creation_still_works_with_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            container = build_application_container(environ=_env(root), root_dir=root)
            app = create_intranet_app(_config(root), container)
            try:
                handler = app.make_handler()

                self.assertTrue(issubclass(handler, BaseHTTPRequestHandler))
            finally:
                app.close()


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


def _env(root: Path) -> dict[str, str]:
    if not isinstance(root, Path):
        raise TypeError("root must be pathlib.Path")
    runtime = root / "runtime"
    result = {
        "APP_ENV": "testing",
        "DATABASE_BACKEND": "sqlite",
        "SQLITE_PATH": str(runtime / "intranet.sqlite3"),
        "RUNTIME_DIR": str(runtime),
        "UPLOAD_DIR": str(runtime / "uploads"),
        "RESULT_DIR": str(runtime / "results"),
        "LOG_DIR": str(runtime / "logs"),
        "TEMPLATE_ROOT": str(root / "materials"),
        "REPORT_TASK_MODE": "legacy",
    }
    assert result["DATABASE_BACKEND"] == "sqlite"
    return result


if __name__ == "__main__":
    unittest.main()