from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.meituan_download_assistant_sync import MEITUAN_REPORT_KEYWORDS, SyncConfig, copy_new_files


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTENSION_ROOT = PROJECT_ROOT / "browser_extensions" / "meituan_download_assistant"


class MeituanDownloadAssistantTests(unittest.TestCase):
    def test_manifest_is_valid_mv3_extension(self) -> None:
        manifest = json.loads((EXTENSION_ROOT / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("downloads", manifest["permissions"])
        self.assertIn("service_worker.js", manifest["background"]["service_worker"])
        self.assertTrue(manifest["content_scripts"])
        self.assertTrue(manifest["content_scripts"][0]["all_frames"])

    def test_report_rules_cover_required_meituan_file_types(self) -> None:
        rules = json.loads((EXTENSION_ROOT / "rules" / "meituan_reports.json").read_text(encoding="utf-8"))
        file_types = {item["file_type"] for item in rules["reports"]}

        self.assertEqual(
            file_types,
            {"product_order", "store_finance", "store_traffic", "service_review"},
        )
        self.assertTrue(rules["guard"]["read_only"])
        self.assertTrue(
            "删除" in rules["guard"]["blocked_action_text"]
            or "鍒犻櫎" in rules["guard"]["blocked_action_text"]
        )

    def test_popup_exposes_batch_export_and_metric_multi_select(self) -> None:
        popup_html = (EXTENSION_ROOT / "popup.html").read_text(encoding="utf-8")
        popup_js = (EXTENSION_ROOT / "popup.js").read_text(encoding="utf-8")

        self.assertIn("metricPanel", popup_html)
        self.assertIn("selectAllMetricsButton", popup_html)
        self.assertIn("autoAllButton", popup_html)
        self.assertIn("METRICS_BY_FILE_TYPE", popup_js)
        self.assertIn("DAILY_FILE_TYPES", popup_js)
        self.assertIn('const DAILY_FILE_TYPES = ["product_order", "store_finance", "store_traffic"];', popup_js)
        self.assertNotIn('const DAILY_FILE_TYPES = ["product_order", "store_finance", "store_traffic", "service_review"];', popup_js)
        self.assertIn("selectedMetrics", popup_js)
        self.assertIn("allFrames: true", popup_js)
        self.assertIn("now.setDate(now.getDate() - 1)", popup_js)
        self.assertIn("商品实付销售额", popup_js)

    def test_content_script_creates_report_then_downloads_from_list(self) -> None:
        content_script = (EXTENSION_ROOT / "content_script.js").read_text(encoding="utf-8")

        self.assertIn("applyDateRange(task)", content_script)
        self.assertIn("selectMetrics(task.metrics", content_script)
        self.assertIn("clickedQuery", content_script)
        self.assertIn("queryButtonText", content_script)
        self.assertIn("createReport(task, rule)", content_script)
        self.assertIn("downloadCreatedReport(task, rule)", content_script)
        self.assertIn("meituanAssistantRunDownloadTask", content_script)
        self.assertIn("日期选择失败", content_script)
        self.assertIn('input.removeAttribute("readonly")', content_script)
        self.assertIn("下载列表", content_script)

    def test_sync_copies_new_files_once_and_writes_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "Downloads" / "meituan_auto_download"
            target_root = root / "target"
            index_path = target_root / "download_index.csv"
            source_file = source_root / "anta_kids" / "instant_retail" / "20260725" / "product_order" / "sample.csv"
            source_file.parent.mkdir(parents=True)
            source_file.write_text("date,amount\n20260725,10\n", encoding="utf-8")

            config = SyncConfig(source_root=source_root, target_root=target_root, index_path=index_path)
            first = copy_new_files(config)
            second = copy_new_files(config)

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 0)
            self.assertTrue((target_root / source_file.relative_to(source_root)).exists())
            index_text = index_path.read_text(encoding="utf-8-sig")
            self.assertIn("sample.csv", index_text)

    def test_sync_plain_downloads_archives_meituan_files_into_raw_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_root = root / "Downloads"
            target_root = root / "target"
            index_path = target_root / "download_index.csv"
            source_root.mkdir(parents=True)
            meituan_file = source_root / "商品数据_20260727_全店数据1785227463695.csv"
            ignored_file = source_root / "普通表格.csv"
            meituan_file.write_text("日期,订单编号\n20260727,1\n", encoding="utf-8")
            ignored_file.write_text("x,y\n1,2\n", encoding="utf-8")

            synced = copy_new_files(
                SyncConfig(
                    source_root=source_root,
                    target_root=target_root,
                    index_path=index_path,
                    file_name_keywords=MEITUAN_REPORT_KEYWORDS,
                    excluded_dir_names=("meituan_auto_download",),
                    structure_meituan_reports=True,
                )
            )

            expected_path = target_root / "anta_kids" / "instant_retail" / "20260727" / "product_order" / meituan_file.name
            self.assertEqual(len(synced), 1)
            self.assertTrue(expected_path.exists())
            self.assertFalse((target_root / ignored_file.name).exists())


if __name__ == "__main__":
    unittest.main()
