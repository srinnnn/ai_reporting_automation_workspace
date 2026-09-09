from __future__ import annotations

from dataclasses import dataclass
import json
import socket
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PrivateDataLocalCenterUnavailable(RuntimeError):
    """Raised when the configured collection service cannot be reached."""


@dataclass(frozen=True)
class UpstreamResponse:
    status_code: int
    body: bytes
    content_type: str


class PrivateDataLocalCenterGateway(Protocol):
    def health(self) -> bool: ...

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> UpstreamResponse: ...


@dataclass(frozen=True)
class PrivateDataLocalCenterClient:
    base_url: str
    timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ValueError("base_url must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))

    def health(self) -> bool:
        try:
            response = self.request("/health")
            payload = json.loads(response.body)
        except (PrivateDataLocalCenterUnavailable, json.JSONDecodeError, UnicodeDecodeError):
            return False
        return isinstance(payload, dict) and response.status_code == 200 and payload.get("status") == "ok"

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> UpstreamResponse:
        if not path.startswith("/"):
            raise ValueError("path must start with slash")
        headers = {"Accept": "*/*"}
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return UpstreamResponse(
                    status_code=response.status,
                    body=response.read(),
                    content_type=response.headers.get("Content-Type", "application/octet-stream"),
                )
        except HTTPError as exc:
            return UpstreamResponse(
                status_code=exc.code,
                body=exc.read(),
                content_type=exc.headers.get("Content-Type", "application/json"),
            )
        except (URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise PrivateDataLocalCenterUnavailable("private data local center is unavailable") from exc
