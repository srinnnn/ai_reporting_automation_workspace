from __future__ import annotations

import json
import os
import unittest

from backend.repositories.interfaces import FoundationCheckRecord, FoundationRepository
from backend.services.ai_content_service import AIContentService
from backend.services.ai_service import AIService, AIRetryPolicy
from intranet_app.ai_gateway import AiGatewayError, BailianSettings, ConnectionTestResult
from intranet_app.content_pipeline import ANTA_DEFAULT_BRAND_PROFILE, DEFAULT_FORBIDDEN_WORDS, P2ContentRequest
from intranet_app.domain import ValidationError


class AIServiceTests(unittest.TestCase):
    def test_ai_configuration_missing_raises_before_provider_call(self) -> None:
        service = AIService(
            settings=BailianSettings(base_url="https://example.com", model="qwen-plus", api_key=""),
            client_factory=_unexpected_client_factory,
        )

        status = service.configuration_status()

        self.assertFalse(status.configured)
        with self.assertRaisesRegex(AiGatewayError, "not configured"):
            service.generate_text("system", "user", 32)

    def test_ai_normal_call_uses_mock_client(self) -> None:
        fake_client = _FakeClient(text="generated copy")

        service = AIService(
            settings=_configured_settings(),
            client_factory=lambda settings, timeout_seconds: fake_client,
            timeout_seconds=7,
        )

        result = service.generate_text("system", "user", 32)

        self.assertEqual(result, "generated copy")
        self.assertEqual(fake_client.calls, [("system", "user", 32)])

    def test_ai_api_exception_is_raised_after_retries(self) -> None:
        fake_client = _FakeClient(error=AiGatewayError("provider failed"))
        service = AIService(
            settings=_configured_settings(),
            client_factory=lambda settings, timeout_seconds: fake_client,
            retry_policy=AIRetryPolicy(max_attempts=2),
        )

        with self.assertRaisesRegex(AiGatewayError, "after retry"):
            service.generate_text("system", "user", 32)

        self.assertEqual(len(fake_client.calls), 2)

    def test_ai_invalid_return_format_is_rejected(self) -> None:
        fake_client = _FakeClient(text={"bad": "shape"})
        service = AIService(
            settings=_configured_settings(),
            client_factory=lambda settings, timeout_seconds: fake_client,
        )

        with self.assertRaisesRegex(AiGatewayError, "invalid text"):
            service.generate_text("system", "user", 32)


class AIContentServiceTests(unittest.TestCase):
    def test_ai_content_service_uses_foundation_rows_and_pipeline(self) -> None:
        foundation_repository = _FakeFoundationRepository()
        fake_client = _FakeClient(text=_valid_ai_response())
        ai_service = AIService(
            settings=_configured_settings(),
            client_factory=lambda settings, timeout_seconds: fake_client,
        )
        service = AIContentService(foundation_repository, ai_service)

        result = service.build_content_pack(_request())

        self.assertEqual(result.module, "p2_content_center")
        self.assertEqual(len(result.output_rows), 1)
        self.assertIn(("anta_kids", "meituan", "instant_retail", "product_order"), foundation_repository.queries)
        self.assertIn(("anta_kids", "meituan", "instant_retail", "service_review"), foundation_repository.queries)
        self.assertEqual(fake_client.calls[0][2], 2600)

    def test_ai_content_service_rejects_invalid_ai_json_from_pipeline(self) -> None:
        foundation_repository = _FakeFoundationRepository()
        fake_client = _FakeClient(text="not json")
        ai_service = AIService(
            settings=_configured_settings(),
            client_factory=lambda settings, timeout_seconds: fake_client,
        )
        service = AIContentService(foundation_repository, ai_service)

        with self.assertRaises(ValidationError):
            service.build_content_pack(_request())


class _FakeClient:
    def __init__(self, text: object | None = None, error: AiGatewayError | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[tuple[str, str, int]] = []

    def generate_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 1600) -> object:
        self.calls.append((system_prompt, user_prompt, max_tokens))
        if self.error is not None:
            raise self.error
        return self.text

    def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(provider="bailian", model="qwen-plus", message="ok")


class _FakeFoundationRepository(FoundationRepository):
    def __init__(self) -> None:
        self.queries: list[tuple[str, str, str, str]] = []

    def save_foundation_check(self, record: FoundationCheckRecord) -> None:
        raise NotImplementedError

    def save_foundation_rows(self, import_batch_id: str, plan: object) -> None:
        raise NotImplementedError

    def query_foundation_rows(
        self,
        brand_id: str,
        platform: str,
        channel: str,
        file_type: str,
    ) -> list[dict[str, str]]:
        self.queries.append((brand_id, platform, channel, file_type))
        if file_type == "product_order":
            return _product_rows()
        return []


def _configured_settings() -> BailianSettings:
    previous_value = os.environ.get("DASHSCOPE_API_KEY")
    os.environ["DASHSCOPE_API_KEY"] = "configured-for-unit-test"
    try:
        return BailianSettings.from_environment()
    finally:
        if previous_value is None:
            os.environ.pop("DASHSCOPE_API_KEY", None)
        else:
            os.environ["DASHSCOPE_API_KEY"] = previous_value


def _unexpected_client_factory(settings: BailianSettings, timeout_seconds: int) -> _FakeClient:
    raise AssertionError("client factory should not be called when API key is missing")


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


def _valid_ai_response() -> str:
    return json.dumps(
        {
            "items": [
                {
                    "sku_code": "sku_ufo8",
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


if __name__ == "__main__":
    unittest.main()
