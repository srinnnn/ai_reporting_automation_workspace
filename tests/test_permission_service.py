from __future__ import annotations

import unittest
from dataclasses import dataclass

from backend.services.permission_service import PermissionService
from backend.services.task_query_service import TaskReadModel
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class PermissionServiceTests(unittest.TestCase):
    def test_admin_can_view_all_tasks(self) -> None:
        service = PermissionService()
        tasks = [_task(1, "alice"), _task(2, "bob")]

        visible = service.filter_visible_tasks(_user("admin", "admin"), tasks)

        self.assertEqual([task.task_id for task in visible], [1, 2])

    def test_regular_user_can_only_view_own_tasks(self) -> None:
        service = PermissionService()
        tasks = [_task(1, "alice"), _task(2, "bob")]

        visible = service.filter_visible_tasks(_user("alice", "operator"), tasks)

        self.assertEqual([task.task_id for task in visible], [1])
        self.assertTrue(service.can_view_task(_user("alice", "operator"), tasks[0]))
        self.assertFalse(service.can_view_task(_user("alice", "operator"), tasks[1]))

    def test_download_requires_visible_success_task_with_result_asset(self) -> None:
        service = PermissionService()
        user = _user("alice", "operator")

        self.assertTrue(service.can_download_task(user, _task(1, "alice", "success", {"result_asset": {"filename": "daily.csv"}})))
        self.assertFalse(service.can_download_task(user, _task(2, "alice", "failed", {"result_asset": {"filename": "daily.csv"}})))
        self.assertFalse(service.can_download_task(user, _task(3, "alice", "success", {})))
        self.assertFalse(service.can_download_task(user, _task(4, "bob", "success", {"result_asset": {"filename": "daily.csv"}})))

    def test_viewer_cannot_submit_task(self) -> None:
        service = PermissionService()

        self.assertFalse(service.can_submit_task(_user("viewer", "viewer"), "REPORT_GENERATE", {"brand_id": "anta_kids"}))
        self.assertTrue(service.can_submit_task(_user("operator", "operator"), "REPORT_GENERATE", {"brand_id": "anta_kids"}))

    def test_business_owner_can_view_scoped_brand_task(self) -> None:
        service = PermissionService()
        user = _user("owner", "Business Owner|brand_id=anta_kids")

        self.assertTrue(service.can_view_task(user, _scoped_task("anta_kids", "anta_retail_team")))
        self.assertFalse(service.can_view_task(user, _scoped_task("bosch", "bosch_team")))

    def test_business_owner_can_view_scoped_task_read_model_fields(self) -> None:
        service = PermissionService()
        user = _user("owner", "Business Owner|business_unit=anta_retail_team")

        self.assertTrue(
            service.can_view_task(
                user,
                _task(
                    10,
                    "other",
                    brand_id="anta_kids",
                    business_unit="anta_retail_team",
                    platform="meituan",
                    channel="instant_retail",
                ),
            )
        )


def _user(username: str, role: str) -> UserRecord:
    return UserRecord(
        id=1,
        username=username,
        display_name=username.title(),
        role=role,
        password_hash=PasswordHash("salt", "digest"),
    )


def _task(
    task_id: int,
    created_by: str,
    status: str = "success",
    result: dict[str, object] | None = None,
    brand_id: str = "",
    business_unit: str = "",
    platform: str = "",
    channel: str = "",
) -> TaskReadModel:
    return TaskReadModel(
        task_id=task_id,
        task_type="REPORT_GENERATE",
        status=status,
        created_by=created_by,
        created_time="2026-07-31T10:20:00+08:00",
        result=result or {},
        error="",
        owner=created_by,
        brand_id=brand_id,
        business_unit=business_unit,
        platform=platform,
        channel=channel,
        updated_at="2026-07-31T10:21:00+08:00",
    )


@dataclass(frozen=True)
class ScopedTask:
    task_id: int
    created_by: str
    status: str
    result: dict[str, object]
    brand_id: str
    business_unit: str


def _scoped_task(brand_id: str, business_unit: str) -> ScopedTask:
    return ScopedTask(
        task_id=10,
        created_by="other",
        status="success",
        result={"result_asset": {"filename": "daily.csv"}},
        brand_id=brand_id,
        business_unit=business_unit,
    )


if __name__ == "__main__":
    unittest.main()
