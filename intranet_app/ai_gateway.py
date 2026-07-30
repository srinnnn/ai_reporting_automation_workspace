from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_BAILIAN_MODEL = "qwen-plus"


class AiGatewayError(RuntimeError):
    """Raised when an AI provider cannot return a valid response."""


@dataclass(frozen=True)
class BailianSettings:
    base_url: str
    model: str
    api_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.base_url, str) or not self.base_url.strip():
            raise ValueError("base_url must not be empty")
        if not self.base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must not be empty")
        if not isinstance(self.api_key, str):
            raise TypeError("api_key must be text")

    @classmethod
    def from_environment(cls) -> "BailianSettings":
        result = cls(
            base_url=os.environ.get("BAILIAN_BASE_URL", DEFAULT_BAILIAN_BASE_URL).rstrip("/"),
            model=os.environ.get("BAILIAN_MODEL", DEFAULT_BAILIAN_MODEL).strip(),
            api_key=_read_user_setting("DASHSCOPE_API_KEY"),
        )
        assert result.base_url and result.model
        return result

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def masked_key(self) -> str:
        if not self.api_key:
            return "未配置"
        if len(self.api_key) <= 8:
            return "已配置"
        return f"{self.api_key[:3]}***{self.api_key[-4:]}"


@dataclass(frozen=True)
class ConnectionTestResult:
    provider: str
    model: str
    message: str

    def __post_init__(self) -> None:
        for value in (self.provider, self.model, self.message):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("connection test fields must not be empty")


class BailianClient:
    def __init__(self, settings: BailianSettings, timeout_seconds: int = 30) -> None:
        if not isinstance(settings, BailianSettings):
            raise TypeError("settings must be BailianSettings")
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")
        self.settings = settings
        self.timeout_seconds = timeout_seconds

    def test_connection(self) -> ConnectionTestResult:
        if not self.settings.is_configured:
            raise AiGatewayError("尚未配置百炼API Key，请先在工作台主机运行 configure_bailian_api_key.bat 并重启工作台。")
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": "你是API连通性检查助手。"},
                {"role": "user", "content": "只回复四个字：连接成功"},
            ],
            "temperature": 0,
            "max_tokens": 16,
        }
        response = self._post_json("/chat/completions", payload)
        message = _extract_message(response)
        result = ConnectionTestResult(provider="阿里云百炼", model=self.settings.model, message=message)
        logging.info("bailian connection test completed with model %s", self.settings.model)
        assert result.message
        return result

    def generate_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 1600) -> str:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError("system_prompt must not be empty")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("user_prompt must not be empty")
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")
        if not self.settings.is_configured:
            raise AiGatewayError("尚未配置百炼API Key，P2正式内容生产不能使用模板文案冒充AI生成。请先在AI接口配置页保存并测试API Key。")
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        response = self._post_json("/chat/completions", payload)
        result = _extract_message(response)
        logging.info("bailian text generation completed with model %s", self.settings.model)
        assert result
        return result

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise ValueError("endpoint must start with slash")
        if not isinstance(payload, dict) or not payload:
            raise ValueError("payload must be a non-empty dict")
        request = Request(
            f"{self.settings.base_url}{endpoint}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            logging.error("bailian HTTP error: status=%s", exc.code)
            raise AiGatewayError(f"百炼接口返回HTTP {exc.code}，请检查API Key、模型权限和账户额度。") from exc
        except URLError as exc:
            logging.error("bailian network error: %s", type(exc.reason).__name__)
            raise AiGatewayError("无法连接百炼接口，请检查工作台主机的网络和代理设置。") from exc
        except TimeoutError as exc:
            logging.error("bailian connection timed out")
            raise AiGatewayError("百炼接口连接超时，请稍后重试。") from exc
        if not raw_body:
            raise AiGatewayError("百炼接口返回空结果。")
        try:
            parsed = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AiGatewayError("百炼接口返回了无法解析的结果。") from exc
        if not isinstance(parsed, dict):
            raise AiGatewayError("百炼接口返回格式不正确。")
        assert isinstance(parsed, dict)
        return parsed


def _extract_message(response: dict[str, Any]) -> str:
    if not isinstance(response, dict):
        raise TypeError("response must be dict")
    try:
        choices = response["choices"]
        if not isinstance(choices, list) or not choices:
            raise KeyError("choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise TypeError("choice must be dict")
        message = first_choice["message"]
        if not isinstance(message, dict):
            raise TypeError("message must be dict")
        content = message["content"]
    except (KeyError, TypeError, IndexError) as exc:
        raise AiGatewayError("百炼接口响应缺少文案内容。") from exc
    if not isinstance(content, str) or not content.strip():
        raise AiGatewayError("百炼接口返回的文案内容为空。")
    result = content.strip()
    assert result
    return result


def _read_user_setting(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("setting name must not be empty")
    process_value = os.environ.get(name, "").strip()
    if process_value or os.name != "nt":
        return process_value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            registry_value, _ = winreg.QueryValueEx(key, name)
    except (FileNotFoundError, OSError):
        return ""
    if not isinstance(registry_value, str):
        logging.error("Windows user setting %s is not text", name)
        return ""
    result = registry_value.strip()
    assert isinstance(result, str)
    return result


def save_bailian_api_key(api_key: str) -> None:
    if not isinstance(api_key, str):
        raise TypeError("api_key must be text")
    normalized = api_key.strip()
    if not normalized:
        raise ValueError("API Key不能为空。")
    if not normalized.startswith("sk-") or len(normalized) < 12:
        raise ValueError("API Key格式不正确，应为百炼控制台创建的通用API Key。")
    if any(character.isspace() for character in normalized):
        raise ValueError("API Key不能包含空格或换行。")
    if os.name == "nt":
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            winreg.SetValueEx(key, "DASHSCOPE_API_KEY", 0, winreg.REG_SZ, normalized)
    os.environ["DASHSCOPE_API_KEY"] = normalized
    logging.info("bailian API key configured for current Windows user")
    assert BailianSettings.from_environment().is_configured
