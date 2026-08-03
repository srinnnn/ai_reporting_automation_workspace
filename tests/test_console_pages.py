from __future__ import annotations

import io
import unittest
from types import SimpleNamespace

from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class ConsolePageTests(unittest.TestCase):
    def test_console_dashboard_page_uses_dashboard_api(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_dashboard_page(_user(role="admin"))

        self.assertIn("Developer Console", page)
        self.assertIn("/api/console/dashboard", page)
        self.assertIn("Total Tasks", page)
        self.assertIn("Recent Failed Tasks", page)

    def test_console_tasks_page_uses_task_api(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_tasks_page(_user(role="developer"))

        self.assertIn("Task Center", page)
        self.assertIn("/api/tasks", page)
        self.assertIn("task_id", page)
        self.assertIn("created_time", page)

    def test_console_environment_page_uses_config_api(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_environment_page(_user(role="admin"))

        self.assertIn("Environment Center", page)
        self.assertIn("/api/system/config/status", page)
        self.assertIn("APP_ENV", page)
        self.assertIn("DATABASE_BACKEND", page)

    def test_business_owner_can_open_dashboard_and_tasks_but_not_environment(self) -> None:
        app = object.__new__(IntranetApp)
        user = _user(username="owner", role="business_owner|brand_id=anta")

        dashboard = app._console_dashboard_page(user)
        tasks = app._console_tasks_page(user)
        environment = app._console_environment_page(user)

        self.assertIn("/api/console/dashboard", dashboard)
        self.assertIn("/api/tasks", tasks)
        self.assertIn("Access denied", environment)

    def test_viewer_is_denied_console_pages(self) -> None:
        app = object.__new__(IntranetApp)
        user = _user(username="viewer", role="viewer")

        self.assertIn("Access denied", app._console_dashboard_page(user))
        self.assertIn("Access denied", app._console_tasks_page(user))
        self.assertIn("Access denied", app._console_environment_page(user))

    def test_console_routes_render_pages(self) -> None:
        app = object.__new__(IntranetApp)
        app._context = lambda handler: SimpleNamespace(user=_user(role="admin"), token="token")
        sent: dict[str, object] = {}
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
        handler = _Handler("/console")

        app.handle_get(handler)

        self.assertEqual(sent["status"], 200)
        self.assertIn("/api/console/dashboard", str(sent["content"]))


def _user(username: str = "admin", role: str = "admin") -> UserRecord:
    return UserRecord(
        id=1,
        username=username,
        display_name=username.title(),
        role=role,
        password_hash=PasswordHash("salt", "digest"),
    )


class _Handler:
    def __init__(self, path: str) -> None:
        self.path = path
        self.wfile = io.BytesIO()


if __name__ == "__main__":
    unittest.main()
