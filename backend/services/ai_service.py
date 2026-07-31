from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol

from intranet_app.ai_gateway import AiGatewayError, BailianClient, BailianSettings, ConnectionTestResult


class TextGenerationClient(Protocol):
    def generate_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 1600) -> str:
        raise NotImplementedError

    def test_connection(self) -> ConnectionTestResult:
        raise NotImplementedError


@dataclass(frozen=True)
class AIRetryPolicy:
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or self.max_attempts <= 0:
            raise ValueError("max_attempts must be a positive integer")


@dataclass(frozen=True)
class AIConfigurationStatus:
    provider: str
    model: str
    configured: bool
    message: str

    def __post_init__(self) -> None:
        for field_name, field_value in (
            ("provider", self.provider),
            ("model", self.model),
            ("message", self.message),
        ):
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(self.configured, bool):
            raise TypeError("configured must be bool")


class AIService:
    def __init__(
        self,
        settings: BailianSettings | None = None,
        client_factory: Callable[[BailianSettings, int], TextGenerationClient] | None = None,
        timeout_seconds: int = 30,
        retry_policy: AIRetryPolicy | None = None,
    ) -> None:
        if settings is not None and not isinstance(settings, BailianSettings):
            raise TypeError("settings must be BailianSettings")
        if client_factory is not None and not callable(client_factory):
            raise TypeError("client_factory must be callable")
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")
        if retry_policy is not None and not isinstance(retry_policy, AIRetryPolicy):
            raise TypeError("retry_policy must be AIRetryPolicy")

        self._settings = settings or BailianSettings.from_environment()
        self._client_factory = client_factory or _default_bailian_client_factory
        self._timeout_seconds = timeout_seconds
        self._retry_policy = retry_policy or AIRetryPolicy()

    def configuration_status(self) -> AIConfigurationStatus:
        configured = self._settings.is_configured
        result = AIConfigurationStatus(
            provider="bailian",
            model=self._settings.model,
            configured=configured,
            message="configured" if configured else "missing_api_key",
        )
        assert isinstance(result, AIConfigurationStatus)
        return result

    def test_connection(self) -> ConnectionTestResult:
        self._ensure_configured()
        result = self._make_client().test_connection()
        assert isinstance(result, ConnectionTestResult)
        return result

    def generate_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 1600) -> str:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError("system_prompt must not be empty")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("user_prompt must not be empty")
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer")

        self._ensure_configured()
        last_error: AiGatewayError | None = None
        for attempt_index in range(self._retry_policy.max_attempts):
            try:
                raw_result = self._make_client().generate_text(system_prompt, user_prompt, max_tokens)
            except AiGatewayError as exc:
                last_error = exc
                logging.warning(
                    "AI text generation failed: provider=%s model=%s attempt=%s/%s error=%s",
                    "bailian",
                    self._settings.model,
                    attempt_index + 1,
                    self._retry_policy.max_attempts,
                    type(exc).__name__,
                )
                continue
            if not isinstance(raw_result, str) or not raw_result.strip():
                raise AiGatewayError("AI provider returned invalid text content")
            normalized = raw_result.strip()
            assert normalized
            return normalized
        raise AiGatewayError("AI text generation failed after retry attempts") from last_error

    def _make_client(self) -> TextGenerationClient:
        client = self._client_factory(self._settings, self._timeout_seconds)
        assert client is not None
        return client

    def _ensure_configured(self) -> None:
        if not self._settings.is_configured:
            raise AiGatewayError("AI API key is not configured")


def _default_bailian_client_factory(settings: BailianSettings, timeout_seconds: int) -> TextGenerationClient:
    if not isinstance(settings, BailianSettings):
        raise TypeError("settings must be BailianSettings")
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive integer")
    return BailianClient(settings, timeout_seconds)
