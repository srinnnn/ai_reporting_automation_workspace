from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from intranet_app.ai_gateway import AiGatewayError, BailianClient, BailianSettings, save_bailian_api_key


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = io.BytesIO(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body.read()


class BailianClientTests(unittest.TestCase):
    def test_connection_returns_model_message(self) -> None:
        settings = BailianSettings("https://example.test/v1", "qwen-plus", "sk-test-key")
        response = _FakeResponse({"choices": [{"message": {"content": "连接成功"}}]})
        with patch("intranet_app.ai_gateway.urlopen", return_value=response):
            result = BailianClient(settings).test_connection()
        self.assertEqual(result.provider, "阿里云百炼")
        self.assertEqual(result.model, "qwen-plus")
        self.assertEqual(result.message, "连接成功")

    def test_connection_rejects_empty_key(self) -> None:
        settings = BailianSettings("https://example.test/v1", "qwen-plus", "")
        with self.assertRaisesRegex(AiGatewayError, "尚未配置"):
            BailianClient(settings).test_connection()

    def test_connection_rejects_missing_content(self) -> None:
        settings = BailianSettings("https://example.test/v1", "qwen-plus", "sk-test-key")
        response = _FakeResponse({"choices": []})
        with patch("intranet_app.ai_gateway.urlopen", return_value=response):
            with self.assertRaisesRegex(AiGatewayError, "缺少文案内容"):
                BailianClient(settings).test_connection()

    def test_settings_mask_api_key(self) -> None:
        settings = BailianSettings("https://example.test/v1", "qwen-plus", "sk-1234567890")
        self.assertEqual(settings.masked_key, "sk-***7890")

    def test_save_key_rejects_invalid_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "格式不正确"):
            save_bailian_api_key("invalid-key")

    def test_save_key_updates_process_environment(self) -> None:
        with patch("intranet_app.ai_gateway.os.name", "posix"):
            with patch.dict("os.environ", {}, clear=False):
                save_bailian_api_key("sk-test-key-123456")
                self.assertTrue(BailianSettings.from_environment().is_configured)


if __name__ == "__main__":
    unittest.main()
