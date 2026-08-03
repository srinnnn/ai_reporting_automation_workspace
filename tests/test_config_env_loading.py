from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core.config import load_core_config


class ConfigEnvLoadingTests(unittest.TestCase):
    def test_dotenv_report_task_mode_is_loaded_when_system_env_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("REPORT_TASK_MODE=task\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                config = load_core_config(root_dir=root)

        self.assertEqual(config.report_task_mode, "task")

    def test_system_environment_overrides_dotenv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("REPORT_TASK_MODE=task\n", encoding="utf-8")
            with patch.dict(os.environ, {"REPORT_TASK_MODE": "legacy"}, clear=True):
                config = load_core_config(root_dir=root)

        self.assertEqual(config.report_task_mode, "legacy")

    def test_missing_environment_and_dotenv_keeps_legacy_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.dict(os.environ, {}, clear=True):
                config = load_core_config(root_dir=root)

        self.assertEqual(config.report_task_mode, "legacy")


    def test_dotenv_with_utf8_bom_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("REPORT_TASK_MODE=task\n", encoding="utf-8-sig")
            with patch.dict(os.environ, {}, clear=True):
                config = load_core_config(root_dir=root)

        self.assertEqual(config.report_task_mode, "task")


if __name__ == "__main__":
    unittest.main()


