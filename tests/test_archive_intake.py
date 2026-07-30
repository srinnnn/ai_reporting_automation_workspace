from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from intranet_app.archive_intake import ArchiveIntakeConfig, ensure_intake_workspace, rebuild_archive_catalog, run_archive_intake


class ArchiveIntakeTests(unittest.TestCase):
    def test_archives_known_file_and_updates_index_and_dictionary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            package_root = Path(tmp_dir) / "materials"
            package_root.mkdir()
            config = ArchiveIntakeConfig(package_root)
            ensure_intake_workspace(config)
            source_path = config.intake_pending_dir / "安踏_美团_上下架_商品下载_20260713.xlsx"
            _write_xlsx(source_path, ["app_spu_code", "商品名称", "上下架状态"], ["A10001", "商品A", "上架"])

            result = run_archive_intake(config)

            self.assertEqual(result.processed_count, 1)
            self.assertEqual(result.unresolved_count, 0)
            archive_path = package_root / "03_config_automation_materials" / "03-1_anta_instant_retail" / "03-1-1_listing_filter" / source_path.name
            self.assertTrue(archive_path.exists())
            self.assertFalse(source_path.exists())
            index_rows = _read_csv(config.index_path)
            self.assertEqual(index_rows[0]["优先级"], "P3")
            self.assertEqual(index_rows[0]["项目"], "安踏即时零售")
            dictionary_rows = _read_csv(config.dictionary_path)
            field_names = {row["字段名"] for row in dictionary_rows}
            self.assertIn("app_spu_code", field_names)
            self.assertIn("商品名称", field_names)

    def test_moves_unknown_file_to_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            package_root = Path(tmp_dir) / "materials"
            package_root.mkdir()
            config = ArchiveIntakeConfig(package_root)
            ensure_intake_workspace(config)
            source_path = config.intake_pending_dir / "完全无法识别.xlsx"
            _write_xlsx(source_path, ["字段A"], ["值A"])

            result = run_archive_intake(config)

            self.assertEqual(result.processed_count, 0)
            self.assertEqual(result.unresolved_count, 1)
            unresolved_files = tuple(config.intake_unresolved_dir.rglob("完全无法识别.xlsx"))
            self.assertEqual(len(unresolved_files), 1)

    def test_rebuild_archive_catalog_registers_existing_local_files_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            package_root = Path(tmp_dir) / "materials"
            local_dir = package_root / "01_data_processing" / "01-3_weekly_report" / "anta_weekly_report" / "01_raw_data"
            source_path = local_dir / "0713-0719周美团数据表.xlsx"
            _write_xlsx(source_path, ["商品名称", "支付金额", "订单量"], ["商品A", "100", "2"])
            config = ArchiveIntakeConfig(package_root)

            first_result = rebuild_archive_catalog(config)
            second_result = rebuild_archive_catalog(config)

            self.assertEqual(first_result.processed_count, 1)
            self.assertEqual(second_result.processed_count, 1)
            self.assertTrue(source_path.exists())
            index_rows = _read_csv(config.index_path)
            self.assertEqual(len(index_rows), 1)
            self.assertEqual(index_rows[0]["优先级"], "P1")
            self.assertEqual(index_rows[0]["项目"], "周报")
            self.assertEqual(index_rows[0]["归档路径"], str(source_path))
            dictionary_rows = _read_csv(config.dictionary_path)
            field_names = {row["字段名"] for row in dictionary_rows}
            self.assertEqual(field_names, {"商品名称", "支付金额", "订单量"})


def _write_xlsx(path: Path, headers: list[str], values: list[str]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    sheet.append(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


if __name__ == "__main__":
    unittest.main()
