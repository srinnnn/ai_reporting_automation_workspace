from __future__ import annotations

from pathlib import Path

from .domain import Scenario
from .processors import ai_selection, anta_reporting, bosch_sms, copy_content


ANTA_RETAIL_KEY = "anta_retail"
ANTA_RETAIL_REQUIRED_FIELDS = (
    "上下架筛选：官网货盘、美团商品原表、京东商品原表",
    "素材筛选：待上架清单、素材索引或素材站目录、必要时提供素材站登录 Cookie",
    "黑名单筛选：黑名单明细、美团商品表、京东商品表、门店信息汇总",
)


def build_scenarios(template_root: Path) -> dict[str, Scenario]:
    if not isinstance(template_root, Path):
        raise TypeError("template_root must be pathlib.Path")
    scenarios = {
        bosch_sms.MODULE_KEY: Scenario(
            key=bosch_sms.MODULE_KEY,
            name="博西短彩信数据处理",
            priority="P1",
            brand="博西",
            business_type="数据处理",
            description="上传短彩信发送、到达、点击、订单与成交数据，自动生成追踪指标结果。",
            required_fields=bosch_sms.REQUIRED_FIELDS,
            template_path=template_root / "01_data_processing" / "01-1_sms_mms_processing" / "bosch" / "sms_mms_processing_template.xlsx",
        ),
        anta_reporting.MODULE_KEY: Scenario(
            key=anta_reporting.MODULE_KEY,
            name="安踏周报/月报",
            priority="P1",
            brand="安踏儿童",
            business_type="数据处理",
            description="读取已归档的安踏周报、月报原始数据，生成报表初稿指标和TOP商品。",
            required_fields=anta_reporting.WEEKLY_REQUIRED_FIELDS + anta_reporting.MONTHLY_REQUIRED_FIELDS,
            template_path=template_root / "01_data_processing",
        ),
        ANTA_RETAIL_KEY: Scenario(
            key=ANTA_RETAIL_KEY,
            name="安踏即时零售",
            priority="P3",
            brand="安踏即时零售",
            business_type="配置自动化",
            description="连接已开发的安踏即时零售网页，统一处理上下架筛选、素材筛选、黑名单筛选。",
            required_fields=ANTA_RETAIL_REQUIRED_FIELDS,
            template_path=template_root / "03_config_automation_materials" / "03-1_anta_instant_retail",
        ),
        ai_selection.MODULE_KEY: Scenario(
            key=ai_selection.MODULE_KEY,
            name="AI选品辅助",
            priority="P2",
            brand="多品牌",
            business_type="AI选品",
            description="先选择项目，再上传商品候选池；通用项目和安踏儿童项目使用不同字段口径生成选品分。",
            required_fields=ai_selection.REQUIRED_FIELDS,
            template_path=template_root / "02_brand_content_materials" / "required_materials" / "02_product_selling_points" / "product_selling_points_template.xlsx",
        ),
        copy_content.MODULE_KEY: Scenario(
            key=copy_content.MODULE_KEY,
            name="文案内容辅助",
            priority="P2",
            brand="多品牌",
            business_type="文案内容",
            description="上传品牌调性、商品卖点和禁用词，生成标题/正文建议并输出初步合规检查结果。",
            required_fields=copy_content.REQUIRED_FIELDS,
            template_path=template_root / "02_brand_content_materials" / "required_materials" / "06_copywriting_tasks" / "copy_content_template_anta_kids_example.xlsx",
        ),
    }
    assert len(scenarios) == 5
    return scenarios
