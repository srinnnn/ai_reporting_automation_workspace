from __future__ import annotations

import io
import unittest
from pathlib import Path
from types import SimpleNamespace

from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.storage import UserRecord


class ConsoleTaskEnhancementTests(unittest.TestCase):
    def test_task_center_contains_read_only_filters(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_tasks_page(_user(role="developer"))

        self.assertIn('id="console-task-filter-form"', page)
        self.assertIn('name="task_type"', page)
        self.assertIn('name="status"', page)
        self.assertIn('name="created_by"', page)
        self.assertIn('new URLSearchParams()', page)
        self.assertIn('FormData(form)', page)
        self.assertIn('fetch(`/api/tasks${queryString()}`', page)

    def test_task_center_reuses_existing_detail_page(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_tasks_page(_user(role="admin"))

        self.assertIn('href="${taskUrl(task)}"', page)
        self.assertIn('const taskUrl = (task) => `/tasks/${encodeURIComponent(text(task.task_id))}`;', page)
        self.assertIn('View</a>', page)

    def test_task_center_shows_status_error_and_asset_state(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_tasks_page(_user(role="developer"))

        self.assertIn('console-task-status', page)
        self.assertIn('`console-status-${status}`', page)
        css = Path('intranet_app/static/style.css').read_text(encoding='utf-8')
        self.assertIn('console-status-success', css)
        self.assertIn('console-status-failed', css)
        self.assertIn('errorSummary(task)', page)
        self.assertIn('assetStatus(task)', page)
        self.assertIn('console-asset-ready', page)
        self.assertIn('console-asset-missing', page)

    def test_console_tasks_route_renders_enhanced_page(self) -> None:
        app = object.__new__(IntranetApp)
        app._context = lambda handler: SimpleNamespace(user=_user(role="admin"), token="token")
        sent: dict[str, object] = {}
        app._send_html = lambda handler, content, status=200: sent.update({"content": content, "status": status})
        handler = _Handler("/console/tasks")

        app.handle_get(handler)

        self.assertEqual(sent["status"], 200)
        content = str(sent["content"])
        self.assertIn('id="console-task-filter-form"', content)
        self.assertIn('fetch(`/api/tasks${queryString()}`', content)
        self.assertIn('href="${taskUrl(task)}"', content)

    def test_viewer_cannot_open_enhanced_task_center(self) -> None:
        app = object.__new__(IntranetApp)

        page = app._console_tasks_page(_user(username="viewer", role="viewer"))

        self.assertIn("Access denied", page)
        self.assertNotIn('id="console-task-filter-form"', page)


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
