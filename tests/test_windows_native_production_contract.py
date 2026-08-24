from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsNativeProductionContractTests(unittest.TestCase):
    def test_start_script_uses_fastapi_entry_and_pid_state(self) -> None:
        script = (ROOT / "ops" / "windows-native" / "start-current.ps1").read_text(encoding="utf-8")
        common = (ROOT / "ops" / "windows-native" / "common.ps1").read_text(encoding="utf-8")
        combined = script + common

        self.assertIn("backend.main:app", script)
        self.assertIn("runtime-state.json", combined)
        self.assertIn("current-release.txt", combined)
        self.assertNotIn("intranet_app.app", combined)
        self.assertNotIn("BaseHTTPRequestHandler", combined)

    def test_stop_script_never_kills_every_python_process(self) -> None:
        script = (ROOT / "ops" / "windows-native" / "stop-current.ps1").read_text(encoding="utf-8")

        self.assertIn("Get-Process -Id", script)
        self.assertIn("Stop-Process -Id $pidToStop", script)
        self.assertNotIn("python.exe", script.lower())
        self.assertNotIn("taskkill", script.lower())

    def test_production_runner_is_not_used_for_pr_ci(self) -> None:
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        rollback = (ROOT / ".github" / "workflows" / "rollback.yml").read_text(encoding="utf-8")

        self.assertNotIn("middle-platform-prod-native", ci)
        self.assertIn("workflow_dispatch", deploy)
        self.assertIn("workflow_dispatch", rollback)
        self.assertIn("middle-platform-prod-native", deploy)
        self.assertIn("middle-platform-prod-native", rollback)
        self.assertNotIn("pull_request", deploy)
        self.assertNotIn("pull_request", rollback)

    def test_deploy_rejects_sha_outside_main_history(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        script = (ROOT / "ops" / "windows-native" / "deploy-release.ps1").read_text(encoding="utf-8")

        self.assertIn("git merge-base --is-ancestor $target origin/main", workflow)
        self.assertIn("git merge-base --is-ancestor $TargetSha origin/main", script)


if __name__ == "__main__":
    unittest.main()
