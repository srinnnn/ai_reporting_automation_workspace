from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from backend.core.config import load_core_config
from backend.integrations.private_data_local_center import (
    PrivateDataLocalCenterClient,
    PrivateDataLocalCenterGateway,
    PrivateDataLocalCenterUnavailable,
    UpstreamResponse,
)
from backend.repositories.sqlite.feedback_repository import SQLiteFeedbackRepository
from backend.schemas.platform import IntegrationHealth
from backend.services.feedback_service import FeedbackFilters, FeedbackService
from backend.services.platform_service import PRIVATE_DATA_LOCAL_CENTER_ENTRY_PATH, PlatformService

APP_VERSION = "3.0.0"
ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


def create_app(*, private_data_client: PrivateDataLocalCenterGateway | None = None) -> FastAPI:
    config = load_core_config(root_dir=ROOT_DIR)
    collection_client = private_data_client or PrivateDataLocalCenterClient(
        config.integrations.private_data_local_center_url
    )
    demo_mode = os.environ.get("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}
    service = PlatformService(template_root=config.files.template_root, demo_mode=demo_mode)
    feedback_service = FeedbackService(
        repository=SQLiteFeedbackRepository(config.database.sqlite_path),
        projects=service.projects(),
    )
    app = FastAPI(title="Middle Platform API", version=APP_VERSION)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/ready")
    def ready() -> dict[str, object]:
        runtime_ready = _ensure_directory(config.files.runtime_dir)
        database_ready = _check_sqlite(config.database.sqlite_path)
        frontend_ready = FRONTEND_DIST.joinpath("index.html").exists() if config.environment == "production" else True
        status = "ok" if runtime_ready and database_ready and frontend_ready else "error"
        payload = {
            "status": status,
            "runtime_directory": runtime_ready,
            "database": database_ready,
            "frontend_dist": frontend_ready,
            "environment": config.environment,
        }
        if status != "ok":
            raise HTTPException(status_code=503, detail=payload)
        return payload

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {
            "version": os.environ.get("APP_VERSION", APP_VERSION),
            "commit_sha": os.environ.get("APP_COMMIT_SHA", "local"),
            "build_time": os.environ.get("APP_BUILD_TIME", datetime.now(UTC).isoformat()),
            "environment": config.environment,
        }

    @app.get("/api/v1/dashboard")
    def dashboard() -> dict[str, object]:
        return service.dashboard().model_dump()

    @app.get("/api/v1/brands")
    def brands() -> list[dict[str, object]]:
        return [brand.model_dump() for brand in service.brands()]

    @app.get("/api/v1/brands/{brand_key}")
    def brand(brand_key: str) -> dict[str, object]:
        record = service.brand(brand_key)
        if record is None:
            raise HTTPException(status_code=404, detail="Unknown brand")
        return record.model_dump()

    @app.get("/api/v1/projects")
    def projects() -> list[dict[str, object]]:
        return [project.model_dump() for project in service.projects()]

    @app.get("/api/v1/projects/{project_key}")
    def project(project_key: str) -> dict[str, object]:
        record = service.project(project_key)
        if record is None:
            raise HTTPException(status_code=404, detail="Unknown project")
        return record.model_dump()

    @app.get("/api/v1/integrations/private-data-local-center/health")
    def private_data_local_center_health() -> dict[str, str]:
        available = collection_client.health()
        result = IntegrationHealth(
            service="private-data-local-center",
            status="AVAILABLE" if available else "UNAVAILABLE",
            entry_path=PRIVATE_DATA_LOCAL_CENTER_ENTRY_PATH,
            message="采集需求服务可用" if available else "采集需求服务不可用",
        )
        return result.model_dump()

    async def proxy_collection_request(request: Request, upstream_path: str) -> Response:
        body = await request.body()
        try:
            upstream = await run_in_threadpool(
                collection_client.request,
                upstream_path,
                method=request.method,
                body=body or None,
                content_type=request.headers.get("content-type"),
            )
        except PrivateDataLocalCenterUnavailable as exc:
            raise HTTPException(status_code=502, detail="Private data local center is unavailable") from exc
        return _upstream_response(upstream)

    @app.post("/api/v1/collection-requests")
    async def create_collection_request(request: Request) -> Response:
        return await proxy_collection_request(request, "/api/v1/collection-requests")

    @app.get("/api/v1/collection-requests/{request_id}")
    async def get_collection_request(request_id: str, request: Request) -> Response:
        return await proxy_collection_request(request, f"/api/v1/collection-requests/{request_id}")

    @app.post("/api/v1/collection-requests/{request_id}/draft")
    async def save_collection_request_draft(request_id: str, request: Request) -> Response:
        return await proxy_collection_request(request, f"/api/v1/collection-requests/{request_id}/draft")

    @app.post("/api/v1/collection-requests/{request_id}/submit")
    async def submit_collection_request(request_id: str, request: Request) -> Response:
        return await proxy_collection_request(request, f"/api/v1/collection-requests/{request_id}/submit")

    @app.get("/api/v1/feedback")
    def feedback(
        brand: str | None = None,
        category: str | None = None,
        project: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, object]]:
        try:
            filters = FeedbackFilters(brand=brand, category=category, project=project, status=status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return [record.model_dump() for record in feedback_service.list_feedback(filters)]

    @app.get("/api/v1/schedules")
    def schedules() -> list[dict[str, object]]:
        return [item.model_dump() for item in service.schedule()]

    @app.get("/api/v1/tasks")
    def tasks() -> dict[str, object]:
        return service.module("/tasks", "自动化执行").model_dump()

    @app.get("/api/v1/reports")
    def reports() -> dict[str, object]:
        return service.module("/reports", "报表中心").model_dump()

    @app.get("/api/v1/data-foundation")
    def data_foundation() -> dict[str, object]:
        return service.module("/data-foundation", "数据入库中心").model_dump()

    @app.get("/integrations/private-data-local-center")
    @app.get("/integrations/private-data-local-center/")
    def private_data_local_center_index() -> Response:
        return _proxy_private_data_frontend(collection_client, "/")

    @app.get("/integrations/private-data-local-center/{asset_path:path}")
    def private_data_local_center_asset(asset_path: str) -> Response:
        return _proxy_private_data_frontend(collection_client, f"/{asset_path}")

    if FRONTEND_DIST.joinpath("assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        index = FRONTEND_DIST / "index.html"
        if not index.exists():
            raise HTTPException(status_code=503, detail="Frontend dist is not available")
        return FileResponse(index)

    return app


def _proxy_private_data_frontend(
    client: PrivateDataLocalCenterGateway,
    upstream_path: str,
) -> Response:
    try:
        upstream = client.request(upstream_path)
    except PrivateDataLocalCenterUnavailable as exc:
        raise HTTPException(status_code=502, detail="Private data local center is unavailable") from exc
    if upstream.content_type.partition(";")[0].strip().lower() == "text/html":
        html = upstream.body.decode("utf-8")
        html = html.replace('"/assets/', '"/integrations/private-data-local-center/assets/')
        html = html.replace("'/assets/", "'/integrations/private-data-local-center/assets/")
        upstream = UpstreamResponse(
            status_code=upstream.status_code,
            body=html.encode("utf-8"),
            content_type=upstream.content_type,
        )
    return _upstream_response(upstream)


def _upstream_response(upstream: UpstreamResponse) -> Response:
    return Response(
        content=upstream.body,
        status_code=upstream.status_code,
        headers={"content-type": upstream.content_type},
    )


def _ensure_directory(path: Path) -> bool:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    path.mkdir(parents=True, exist_ok=True)
    return path.exists() and path.is_dir()


def _check_sqlite(path: Path) -> bool:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(path)
        connection.execute("select 1")
        connection.close()
    except sqlite3.Error:
        return False
    return True


app = create_app()
