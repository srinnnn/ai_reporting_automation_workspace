from __future__ import annotations

import tempfile
import unittest
import logging as std_logging
from pathlib import Path

from backend.core.config import load_core_config
from backend.core.health import STATUS_WARNING, check_system_health, health_response
from backend.core.logging import configure_logging, get_logger


class CoreConfigTests(unittest.TestCase):
    def test_loads_development_defaults_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={}, root_dir=Path(temp_dir))

        self.assertEqual(config.environment, "development")
        self.assertEqual(config.database.backend, "sqlite")
        self.assertFalse(config.ai.api_key_configured)
        self.assertEqual(config.ai.model, "qwen-plus")

    def test_rejects_invalid_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                load_core_config(environ={"APP_ENV": "local"}, root_dir=Path(temp_dir))

    def test_postgres_requires_database_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                load_core_config(environ={"DATABASE_BACKEND": "postgres"}, root_dir=Path(temp_dir))


class CoreLoggingTests(unittest.TestCase):
    def test_configure_logging_creates_log_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = load_core_config(environ={"LOG_DIR": str(root / "logs")}, root_dir=root)
            log_dir = configure_logging(config, level="INFO")
            logger = get_logger("tests")
            logger.info("logging smoke test")

            self.assertTrue(log_dir.exists())
            self.assertTrue((log_dir / "app.log").exists())
            std_logging.shutdown()

    def test_rejects_unsupported_level(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={}, root_dir=Path(temp_dir))
            with self.assertRaises(ValueError):
                configure_logging(config, level="DEBUG")


class CoreHealthTests(unittest.TestCase):
    def test_health_response_does_not_expose_ai_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            response = health_response(
                environ={
                    "RUNTIME_DIR": str(Path(temp_dir) / "runtime"),
                    "DASHSCOPE_API_KEY": "sk-test-secret",
                }
            )

        response_text = str(response)
        self.assertIn("components", response)
        self.assertNotIn("sk-test-secret", response_text)

    def test_missing_runtime_is_warning_not_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = load_core_config(environ={}, root_dir=Path(temp_dir))
            result = check_system_health(config)

        self.assertEqual(result.status, STATUS_WARNING)
        self.assertEqual(result.environment, "development")


if __name__ == "__main__":
    unittest.main()
