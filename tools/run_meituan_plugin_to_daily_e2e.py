from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from tools.generate_anta_meituan_daily_batch import BatchDailyResult, generate_batch
from tools.meituan_download_assistant_sync import SyncConfig, SyncedFile, copy_new_files, default_config


@dataclass(frozen=True)
class PluginToDailyResult:
    synced_files: list[SyncedFile]
    daily_results: list[BatchDailyResult]
    intake_root: Path
    output_root: Path

    def __post_init__(self) -> None:
        if not isinstance(self.synced_files, list):
            raise TypeError("synced_files must be list")
        if not isinstance(self.daily_results, list):
            raise TypeError("daily_results must be list")
        if not isinstance(self.intake_root, Path):
            raise TypeError("intake_root must be Path")
        if not isinstance(self.output_root, Path):
            raise TypeError("output_root must be Path")


def run_flow(project_root: Path, plugin_download_root: Path, start_date: str, end_date: str) -> PluginToDailyResult:
    if not isinstance(project_root, Path):
        raise TypeError("project_root must be Path")
    if not isinstance(plugin_download_root, Path):
        raise TypeError("plugin_download_root must be Path")
    if not plugin_download_root.exists():
        raise FileNotFoundError(f"插件下载目录不存在：{plugin_download_root}")

    base_config = default_config(project_root)
    sync_config = SyncConfig(
        source_root=plugin_download_root,
        target_root=base_config.target_root,
        index_path=base_config.index_path,
    )
    synced_files = copy_new_files(sync_config)
    output_root = project_root / "intranet_app" / "runtime" / "results" / f"plugin_to_daily_{start_date}_{end_date}"
    daily_results = generate_batch(start_date, end_date, sync_config.target_root, output_root)
    result = PluginToDailyResult(
        synced_files=synced_files,
        daily_results=daily_results,
        intake_root=sync_config.target_root,
        output_root=output_root,
    )
    assert isinstance(result, PluginToDailyResult)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Meituan plugin-download to Anta daily report flow.")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--plugin-download-root", default=str(Path.home() / "Downloads" / "meituan_auto_download"))
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run_flow(
        project_root=Path(args.project_root),
        plugin_download_root=Path(args.plugin_download_root),
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(f"synced_files={len(result.synced_files)}")
    print(f"intake_root={result.intake_root}")
    print(f"output_root={result.output_root}")
    for item in result.daily_results:
        print(f"{item.report_date},{item.status},{item.output_path},{item.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
