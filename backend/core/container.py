from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from backend.core.config import CoreConfig, load_core_config
from backend.core.logging import configure_logging, get_logger
from backend.repositories.interfaces import FoundationRepository, ReportRepository, TaskRepository, UserRepository
from backend.repositories.sqlite.foundation_repository import SQLiteFoundationRepository
from backend.repositories.sqlite.report_repository import SQLiteReportRepository
from backend.repositories.sqlite.task_repository import SQLiteTaskRepository
from backend.repositories.sqlite.user_repository import SQLiteUserRepository
from backend.services.ai_content_service import AIContentService
from backend.services.ai_service import AIService
from backend.services.assets.asset_service import ResultAssetService
from backend.services.assets.providers.local_provider import LocalStorageProvider
from backend.services.data_foundation_service import DataFoundationService
from backend.services.permission_service import PermissionService
from backend.services.report_service import ReportService
from backend.services.task_query_service import TaskQueryService
from backend.services.task_result_service import TaskResultService
from backend.services.task_service import TaskService
from backend.workers.contracts import TaskType
from backend.workers.executors.ai_content_executor import AIContentExecutor
from backend.workers.executors.data_import_executor import DataImportExecutor
from backend.workers.executors.report_executor import ReportExecutor
from backend.workers.task_runner import TaskRunner
from backend.workers.task_submitter import TaskSubmitter
from intranet_app.storage import AppStorage


@dataclass(frozen=True)
class RepositoryBundle:
    users: UserRepository
    foundation: FoundationRepository
    reports: ReportRepository
    tasks: TaskRepository

    def __post_init__(self) -> None:
        if not isinstance(self.users, UserRepository):
            raise TypeError("users must be UserRepository")
        if not isinstance(self.foundation, FoundationRepository):
            raise TypeError("foundation must be FoundationRepository")
        if not isinstance(self.reports, ReportRepository):
            raise TypeError("reports must be ReportRepository")
        if not isinstance(self.tasks, TaskRepository):
            raise TypeError("tasks must be TaskRepository")


@dataclass(frozen=True)
class ServiceBundle:
    data_foundation: DataFoundationService
    reports: ReportService
    ai: AIService
    ai_content: AIContentService
    result_assets: ResultAssetService
    tasks: TaskService
    task_query: TaskQueryService
    task_result: TaskResultService
    permissions: PermissionService
    task_submitter: TaskSubmitter | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data_foundation, DataFoundationService):
            raise TypeError("data_foundation must be DataFoundationService")
        if not isinstance(self.reports, ReportService):
            raise TypeError("reports must be ReportService")
        if not isinstance(self.ai, AIService):
            raise TypeError("ai must be AIService")
        if not isinstance(self.ai_content, AIContentService):
            raise TypeError("ai_content must be AIContentService")
        if not isinstance(self.result_assets, ResultAssetService):
            raise TypeError("result_assets must be ResultAssetService")
        if not isinstance(self.tasks, TaskService):
            raise TypeError("tasks must be TaskService")
        if not isinstance(self.task_query, TaskQueryService):
            raise TypeError("task_query must be TaskQueryService")
        if not isinstance(self.task_result, TaskResultService):
            raise TypeError("task_result must be TaskResultService")
        if not isinstance(self.permissions, PermissionService):
            raise TypeError("permissions must be PermissionService")
        if self.task_submitter is not None and not isinstance(self.task_submitter, TaskSubmitter):
            raise TypeError("task_submitter must be TaskSubmitter")


@dataclass(frozen=True)
class WorkerBundle:
    data_import_executor: DataImportExecutor
    report_executor: ReportExecutor
    ai_content_executor: AIContentExecutor
    task_runner: TaskRunner
    task_submitter: TaskSubmitter

    def __post_init__(self) -> None:
        if not isinstance(self.data_import_executor, DataImportExecutor):
            raise TypeError("data_import_executor must be DataImportExecutor")
        if not isinstance(self.report_executor, ReportExecutor):
            raise TypeError("report_executor must be ReportExecutor")
        if not isinstance(self.ai_content_executor, AIContentExecutor):
            raise TypeError("ai_content_executor must be AIContentExecutor")
        if not isinstance(self.task_runner, TaskRunner):
            raise TypeError("task_runner must be TaskRunner")
        if not isinstance(self.task_submitter, TaskSubmitter):
            raise TypeError("task_submitter must be TaskSubmitter")


@dataclass(frozen=True)
class ApplicationContainer:
    config: CoreConfig
    logger: logging.Logger
    repositories: RepositoryBundle
    services: ServiceBundle
    workers: WorkerBundle

    def __post_init__(self) -> None:
        if not isinstance(self.config, CoreConfig):
            raise TypeError("config must be CoreConfig")
        if not isinstance(self.logger, logging.Logger):
            raise TypeError("logger must be logging.Logger")
        if not isinstance(self.repositories, RepositoryBundle):
            raise TypeError("repositories must be RepositoryBundle")
        if not isinstance(self.services, ServiceBundle):
            raise TypeError("services must be ServiceBundle")
        if not isinstance(self.workers, WorkerBundle):
            raise TypeError("workers must be WorkerBundle")


    def close(self) -> None:
        for logger in (self.logger, logging.getLogger("ai_reporting_automation")):
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
def build_application_container(
    config: CoreConfig | None = None,
    environ: Mapping[str, str] | None = None,
    root_dir: Path | None = None,
) -> ApplicationContainer:
    actual_config = config if config is not None else load_core_config(environ=environ, root_dir=root_dir)
    if not isinstance(actual_config, CoreConfig):
        raise TypeError("config must be CoreConfig")
    if actual_config.database.backend != "sqlite":
        raise NotImplementedError("ApplicationContainer skeleton supports sqlite only")

    configure_logging(actual_config)
    logger = get_logger("container")
    storage = AppStorage(actual_config.database.sqlite_path)
    repositories = _build_repository_bundle(storage)
    services = _build_service_bundle(actual_config, repositories)
    workers = _build_worker_bundle(services)
    object.__setattr__(services, "task_submitter", workers.task_submitter)
    container = ApplicationContainer(
        config=actual_config,
        logger=logger,
        repositories=repositories,
        services=services,
        workers=workers,
    )
    logger.info("application container initialized: env=%s db=%s", actual_config.environment, actual_config.database.backend)
    assert isinstance(container, ApplicationContainer)
    return container


def _build_repository_bundle(storage: AppStorage) -> RepositoryBundle:
    if not isinstance(storage, AppStorage):
        raise TypeError("storage must be AppStorage")
    bundle = RepositoryBundle(
        users=SQLiteUserRepository(storage),
        foundation=SQLiteFoundationRepository(storage),
        reports=SQLiteReportRepository(storage),
        tasks=SQLiteTaskRepository(storage),
    )
    assert isinstance(bundle, RepositoryBundle)
    return bundle


def _build_service_bundle(config: CoreConfig, repositories: RepositoryBundle) -> ServiceBundle:
    if not isinstance(config, CoreConfig):
        raise TypeError("config must be CoreConfig")
    if not isinstance(repositories, RepositoryBundle):
        raise TypeError("repositories must be RepositoryBundle")
    ai_service = AIService()
    task_query_service = TaskQueryService(repositories.tasks)
    bundle = ServiceBundle(
        data_foundation=DataFoundationService(repositories.foundation),
        reports=ReportService(repositories.foundation, repositories.reports),
        ai=ai_service,
        ai_content=AIContentService(repositories.foundation, ai_service, repositories.reports),
        result_assets=ResultAssetService(LocalStorageProvider(config.files.result_dir)),
        tasks=TaskService(repositories.tasks),
        task_query=task_query_service,
        task_result=TaskResultService(task_query_service, config.files.result_dir),
        permissions=PermissionService(),
    )
    assert isinstance(bundle, ServiceBundle)
    return bundle


def _build_worker_bundle(services: ServiceBundle) -> WorkerBundle:
    if not isinstance(services, ServiceBundle):
        raise TypeError("services must be ServiceBundle")
    data_import_executor = DataImportExecutor(services.data_foundation)
    report_executor = ReportExecutor(services.reports, services.result_assets)
    ai_content_executor = AIContentExecutor(services.ai_content)
    task_runner = TaskRunner(
        {
            TaskType.DATA_IMPORT: data_import_executor,
            TaskType.REPORT_GENERATE: report_executor,
            TaskType.AI_CONTENT_GENERATE: ai_content_executor,
        }
    )
    bundle = WorkerBundle(
        data_import_executor=data_import_executor,
        report_executor=report_executor,
        ai_content_executor=ai_content_executor,
        task_runner=task_runner,
        task_submitter=TaskSubmitter(services.tasks, task_runner),
    )
    assert isinstance(bundle, WorkerBundle)
    return bundle
