from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from intranet_app.app import IntranetApp
from intranet_app.auth import PasswordHash
from intranet_app.config import AppConfig
from intranet_app.content_pipeline import ANTA_DEFAULT_BRAND_PROFILE, DEFAULT_FORBIDDEN_WORDS, P2ContentRequest, build_p2_content_pack
from intranet_app.domain import ValidationError
from intranet_app.storage import UserRecord


class P2ContentPipelineTests(unittest.TestCase):
    def test_build_pack_generates_ai_copy_from_foundation_rows(self) -> None:
        request = _request()
        result = build_p2_content_pack(request, _product_rows(), [], _fake_ai_generate_text)

        self.assertEqual(result.module, "p2_content_center")
        self.assertEqual(result.summary["AI生成状态"], "已调用API生成")
        self.assertEqual(result.output_rows[0]["款号/SKU"], "sku_ufo8")
        self.assertIn("开学季", result.output_rows[0]["AI正文"])
        self.assertIn("轻弹缓震", result.output_rows[0]["卖点提炼"])
        self.assertIn("视觉Brief", result.output_rows[0])

    def test_build_pack_rejects_missing_foundation_product_rows(self) -> None:
        with self.assertRaisesRegex(ValidationError, "基础数据层缺少商品订单数据"):
            build_p2_content_pack(_request(), [], [], _fake_ai_generate_text)

    def test_build_pack_rejects_invalid_ai_json(self) -> None:
        with self.assertRaisesRegex(ValidationError, "合法JSON"):
            build_p2_content_pack(_request(), _product_rows(), [], _invalid_ai_generate_text)


class P2ContentPageTests(unittest.TestCase):
    def test_page_contains_low_input_p2_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "materials").mkdir()
            app = IntranetApp(_config(root))
            user = UserRecord(1, "admin", "系统管理员", "管理员", PasswordHash("salt", "digest"))

            page = app._p2_content_center_page(user, "")

            self.assertIn("P2内容生产中心", page)
            self.assertIn('action="/p2-content-center/run"', page)
            self.assertIn('name="start_date"', page)
            self.assertIn('name="end_date"', page)
            self.assertIn("选品Agent", page)


def _request() -> P2ContentRequest:
    return P2ContentRequest(
        brand_id="anta_kids",
        brand_name="安踏儿童",
        platform="meituan",
        channel="instant_retail",
        start_date="20260720",
        end_date="20260726",
        task_type="social_copy",
        output_count=1,
        brand_profile=ANTA_DEFAULT_BRAND_PROFILE,
        forbidden_words=DEFAULT_FORBIDDEN_WORDS,
    )


def _product_rows() -> list[dict[str, str]]:
    return [
        {
            "日期": "20260725-20260725",
            "订单编号": "order-1",
            "下单时间": "2026-07-25 10:00:00",
            "店铺名称": "西安门店",
            "店铺ID": "store-1",
            "店铺所在城市": "西安",
            "订单状态": "已完成",
            "商品分类": "儿童跑鞋",
            "商品名称": "安踏儿童UFO8男大童跑鞋",
            "UPC码": "",
            "商品SKU码": "sku_ufo8",
            "商品销售数量": "2",
            "商品实付销售额": "399.00",
        }
    ]


def _fake_ai_generate_text(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    payload = json.loads(user_prompt)
    sku_code = payload["products"][0]["sku_code"]
    return json.dumps(
        {
            "items": [
                {
                    "sku_code": sku_code,
                    "target_audience": "大童家长",
                    "usage_scene": "开学季体育课和日常跑步",
                    "selling_points": ["轻弹缓震", "适合校园运动"],
                    "copy_title": "开学季跑鞋推荐",
                    "copy_body": "宝贝开学季，运动量提升，安踏儿童UFO8适合体育课和日常跑步。",
                    "visual_brief": "主图突出跑鞋与校园运动场景，保留商品实拍和品牌识别。",
                    "risk_flags": ["优惠信息待业务确认"],
                }
            ]
        },
        ensure_ascii=False,
    )


def _invalid_ai_generate_text(system_prompt: str, user_prompt: str, max_tokens: int) -> str:
    return "不是JSON"


def _config(root: Path) -> AppConfig:
    return AppConfig(
        host="127.0.0.1",
        port=8765,
        secret_key="test-secret",
        database_path=root / "runtime" / "intranet.sqlite3",
        upload_dir=root / "runtime" / "uploads",
        result_dir=root / "runtime" / "results",
        template_root=root / "materials",
        default_admin_password="admin123",
    )


if __name__ == "__main__":
    unittest.main()
