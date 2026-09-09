from __future__ import annotations

import json
from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient

from backend.integrations.private_data_local_center import (
    PrivateDataLocalCenterClient,
    PrivateDataLocalCenterUnavailable,
)


class FakePrivateDataLocalCenterClient:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.calls: list[dict[str, object]] = []

    def health(self) -> bool:
        return self.available

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        content_type: str | None = None,
    ):
        from backend.integrations.private_data_local_center import (
            PrivateDataLocalCenterUnavailable,
            UpstreamResponse,
        )

        self.calls.append(
            {
                "path": path,
                "method": method,
                "body": body,
                "content_type": content_type,
            }
        )
        if not self.available:
            raise PrivateDataLocalCenterUnavailable("private data local center is unavailable")
        if path == "/":
            html = b'<script type="module" src="/assets/index.js"></script>'
            return UpstreamResponse(status_code=200, body=html, content_type="text/html; charset=utf-8")
        if path == "/assets/index.js":
            return UpstreamResponse(status_code=200, body=b"console.log('ready')", content_type="text/javascript")
        return UpstreamResponse(status_code=201, body=b'{"request_id":"request-a"}', content_type="application/json")


class PrivateDataLocalCenterIntegrationTests(unittest.TestCase):
    def _client(self, upstream: FakePrivateDataLocalCenterClient) -> TestClient:
        root = Path(self.temp_dir.name)
        environment = {
            "APP_ENV": "testing",
            "DEMO_MODE": "false",
            "RUNTIME_DIR": str(root / "runtime"),
            "SQLITE_PATH": str(root / "runtime" / "intranet.sqlite3"),
        }
        with patch.dict("os.environ", environment, clear=False):
            from backend.main import create_app

            return TestClient(create_app(private_data_client=upstream))

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_registers_private_data_center_in_anta_p1_and_projects(self) -> None:
        client = self._client(FakePrivateDataLocalCenterClient())

        brand = client.get("/api/v1/brands/ANTA").json()
        project = client.get("/api/v1/projects/private_data_local_center").json()

        p1 = next(category for category in brand["categories"] if category["key"] == "P1")
        self.assertEqual(p1["capability_count"], 2)
        self.assertIn("私域数据采集中心", [item["name"] for item in p1["capabilities"]])
        self.assertEqual(project["status"], "CONFIGURED")
        self.assertEqual(project["integration_key"], "private-data-local-center")
        self.assertEqual(
            project["entry_path"],
            "/integrations/private-data-local-center/#/collection/requests/new",
        )

    def test_reports_real_upstream_health_without_claiming_connected(self) -> None:
        available = self._client(FakePrivateDataLocalCenterClient(available=True))
        unavailable = self._client(FakePrivateDataLocalCenterClient(available=False))

        self.assertEqual(
            available.get("/api/v1/integrations/private-data-local-center/health").json()["status"],
            "AVAILABLE",
        )
        self.assertEqual(
            unavailable.get("/api/v1/integrations/private-data-local-center/health").json()["status"],
            "UNAVAILABLE",
        )

    def test_proxies_frontend_and_rewrites_root_asset_paths(self) -> None:
        client = self._client(FakePrivateDataLocalCenterClient())

        index = client.get("/integrations/private-data-local-center/")
        asset = client.get("/integrations/private-data-local-center/assets/index.js")

        self.assertEqual(index.status_code, 200)
        self.assertIn('/integrations/private-data-local-center/assets/index.js', index.text)
        self.assertEqual(asset.text, "console.log('ready')")

    def test_rejects_non_asset_paths_under_the_frontend_proxy_prefix(self) -> None:
        upstream = FakePrivateDataLocalCenterClient()
        client = self._client(upstream)

        response = client.get(
            "/integrations/private-data-local-center/api/v1/collection-requests/request-a"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(upstream.calls, [])

    def test_forwards_collection_request_body_and_upstream_status(self) -> None:
        upstream = FakePrivateDataLocalCenterClient()
        client = self._client(upstream)
        payload = {"project_name": "私域项目 A"}

        response = client.post("/api/v1/collection-requests", json=payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"request_id": "request-a"})
        self.assertEqual(upstream.calls[-1]["path"], "/api/v1/collection-requests")
        self.assertEqual(upstream.calls[-1]["method"], "POST")
        self.assertEqual(json.loads(upstream.calls[-1]["body"]), payload)
        self.assertEqual(upstream.calls[-1]["content_type"], "application/json")

    def test_forwards_read_draft_and_submit_to_explicit_upstream_paths(self) -> None:
        upstream = FakePrivateDataLocalCenterClient()
        client = self._client(upstream)

        client.get("/api/v1/collection-requests/request-a")
        client.post("/api/v1/collection-requests/request-a/draft", json={"version": 1})
        client.post("/api/v1/collection-requests/request-a/submit", json={"version": 2})

        self.assertEqual(
            [(call["method"], call["path"]) for call in upstream.calls],
            [
                ("GET", "/api/v1/collection-requests/request-a"),
                ("POST", "/api/v1/collection-requests/request-a/draft"),
                ("POST", "/api/v1/collection-requests/request-a/submit"),
            ],
        )

    def test_unavailable_upstream_fails_closed_with_502(self) -> None:
        client = self._client(FakePrivateDataLocalCenterClient(available=False))

        response = client.post("/api/v1/collection-requests/request-a/submit")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Private data local center is unavailable")


class PrivateDataLocalCenterClientTests(unittest.TestCase):
    def test_health_reads_the_real_health_contract(self) -> None:
        response = _FakeUrlResponse(200, b'{"status":"ok"}', "application/json")
        with patch("backend.integrations.private_data_local_center.urlopen", return_value=response) as urlopen:
            available = PrivateDataLocalCenterClient("http://127.0.0.1:8000").health()

        self.assertTrue(available)
        self.assertEqual(urlopen.call_args.args[0].full_url, "http://127.0.0.1:8000/health")

    def test_http_error_response_is_forwarded_without_masking_validation_details(self) -> None:
        error = HTTPError(
            url="http://127.0.0.1:8000/api/v1/collection-requests",
            code=422,
            msg="Unprocessable Entity",
            hdrs={"Content-Type": "application/json"},
            fp=BytesIO(b'{"detail":"invalid request"}'),
        )
        with patch("backend.integrations.private_data_local_center.urlopen", side_effect=error):
            response = PrivateDataLocalCenterClient("http://127.0.0.1:8000").request(
                "/api/v1/collection-requests",
                method="POST",
                body=b"{}",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.body, b'{"detail":"invalid request"}')

    def test_connection_error_is_translated_to_unavailable(self) -> None:
        with patch(
            "backend.integrations.private_data_local_center.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaises(PrivateDataLocalCenterUnavailable):
                PrivateDataLocalCenterClient("http://127.0.0.1:8000").request("/health")


class _FakeUrlResponse:
    def __init__(self, status: int, body: bytes, content_type: str) -> None:
        self.status = status
        self.body = body
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.body


if __name__ == "__main__":
    unittest.main()
