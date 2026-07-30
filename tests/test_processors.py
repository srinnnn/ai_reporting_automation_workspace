from __future__ import annotations

import unittest

from intranet_app.domain import ValidationError
from intranet_app.processors import ai_selection, anta_blacklist, anta_listing, bosch_sms, copy_content


class BoschSmsProcessorTests(unittest.TestCase):
    def test_process_normal_values(self) -> None:
        result = bosch_sms.process(
            [
                {
                    "品牌": "博西",
                    "发送日期": "2026-07-01",
                    "活动名称": "会员清洁日",
                    "渠道": "短信",
                    "发送量": "1000",
                    "到达量": "960",
                    "点击量": "120",
                    "订单量": "18",
                    "成交金额": "35600.50",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["到达率"], "96.00%")
        self.assertEqual(result.output_rows[0]["点击率"], "12.50%")
        self.assertEqual(result.output_rows[0]["转化率"], "15.00%")
        self.assertEqual(result.output_rows[0]["单次发送产出"], "35.60")

    def test_process_zero_denominator(self) -> None:
        result = bosch_sms.process(
            [
                {
                    "品牌": "博西",
                    "发送日期": "2026-07-01",
                    "活动名称": "空发送测试",
                    "渠道": "短信",
                    "发送量": "0",
                    "到达量": "0",
                    "点击量": "0",
                    "订单量": "0",
                    "成交金额": "0",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["到达率"], "0.00%")
        self.assertEqual(result.output_rows[0]["单次发送产出"], "0.00")

    def test_process_rejects_negative_value(self) -> None:
        with self.assertRaises(ValidationError):
            bosch_sms.process(
                [
                    {
                        "品牌": "博西",
                        "发送日期": "2026-07-01",
                        "活动名称": "异常测试",
                        "渠道": "短信",
                        "发送量": "-1",
                        "到达量": "0",
                        "点击量": "0",
                        "订单量": "0",
                        "成交金额": "0",
                    }
                ]
            )


class AntaListingProcessorTests(unittest.TestCase):
    def test_process_listing_action(self) -> None:
        result = anta_listing.process(
            [
                {
                    "品牌": "安踏",
                    "平台": "天猫",
                    "店铺": "安踏官方旗舰店",
                    "SKU": "ANTA-SKU-001",
                    "商品名称": "跑步鞋A",
                    "动作": "上架",
                    "生效日期": "2026-07-21",
                    "原因": "活动主推",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["导入动作编码"], "ON")
        self.assertEqual(result.summary["上架数量"], "1")

    def test_process_rejects_empty_sku(self) -> None:
        with self.assertRaises(ValidationError):
            anta_listing.process(
                [
                    {
                        "品牌": "安踏",
                        "平台": "天猫",
                        "店铺": "安踏官方旗舰店",
                        "SKU": "",
                        "商品名称": "跑步鞋A",
                        "动作": "上架",
                        "生效日期": "2026-07-21",
                        "原因": "活动主推",
                    }
                ]
            )

    def test_process_rejects_unknown_action(self) -> None:
        with self.assertRaises(ValidationError):
            anta_listing.process(
                [
                    {
                        "品牌": "安踏",
                        "平台": "天猫",
                        "店铺": "安踏官方旗舰店",
                        "SKU": "ANTA-SKU-001",
                        "商品名称": "跑步鞋A",
                        "动作": "暂停",
                        "生效日期": "2026-07-21",
                        "原因": "活动主推",
                    }
                ]
            )


class AntaBlacklistProcessorTests(unittest.TestCase):
    def test_process_blacklist_action_and_masking(self) -> None:
        result = anta_blacklist.process(
            [
                {
                    "品牌": "安踏",
                    "平台": "天猫",
                    "店铺": "安踏官方旗舰店",
                    "账号标识": "13800138000",
                    "动作": "加入黑名单",
                    "原因": "恶意下单",
                    "提交人": "张三",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["导入动作编码"], "BLOCK")
        self.assertEqual(result.output_rows[0]["账号标识_脱敏"], "13*******00")

    def test_process_duplicate_account_warning(self) -> None:
        row = {
            "品牌": "安踏",
            "平台": "天猫",
            "店铺": "安踏官方旗舰店",
            "账号标识": "user_001",
            "动作": "加入黑名单",
            "原因": "恶意下单",
            "提交人": "张三",
        }
        result = anta_blacklist.process([row, row])
        self.assertEqual(len(result.warnings), 1)

    def test_process_rejects_missing_submitter(self) -> None:
        with self.assertRaises(ValidationError):
            anta_blacklist.process(
                [
                    {
                        "品牌": "安踏",
                        "平台": "天猫",
                        "店铺": "安踏官方旗舰店",
                        "账号标识": "13800138000",
                        "动作": "加入黑名单",
                        "原因": "恶意下单",
                        "提交人": "",
                    }
                ]
            )


class AiSelectionProcessorTests(unittest.TestCase):
    def test_process_generic_high_priority_product(self) -> None:
        result = ai_selection.process(
            [
                {
                    "项目": "通用选品",
                    "品牌": "安踏",
                    "平台": "天猫",
                    "商品ID": "ANTA-SKU-101",
                    "商品名称": "轻量跑鞋",
                    "类目": "跑步鞋",
                    "售价": "399",
                    "近30天销量": "260",
                    "库存": "180",
                    "毛利率": "35",
                    "活动匹配度": "92",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["项目"], "通用选品")
        self.assertEqual(result.output_rows[0]["AI选品分"], "75.48")
        self.assertEqual(result.output_rows[0]["推荐优先级"], "高")
        self.assertIn("近期销量强", result.output_rows[0]["推荐理由"])

    def test_process_anta_high_priority_product(self) -> None:
        result = ai_selection.process(
            [
                {
                    "项目": "安踏儿童",
                    "平台": "美团",
                    "款号": "312635583",
                    "商品名称": "UFO8男大童跑步系列秋季跑鞋",
                    "大类": "鞋类",
                    "类目": "跑步鞋",
                    "近7天销量": "52",
                    "近7天销售额": "20221.14",
                    "近30天销量": "212",
                    "库存": "180",
                    "场景主题": "暑期出行穿搭",
                    "选品角色": "核心推荐",
                    "活动匹配度": "92",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["项目"], "安踏儿童")
        self.assertEqual(result.output_rows[0]["AI选品分"], "79.09")
        self.assertEqual(result.output_rows[0]["推荐优先级"], "高")
        self.assertIn("近7天动销强", result.output_rows[0]["推荐理由"])

    def test_process_low_product_with_zero_values(self) -> None:
        result = ai_selection.process(
            [
                {
                    "项目": "安踏儿童",
                    "平台": "京东",
                    "款号": "ANTA-SKU-000",
                    "商品名称": "测试商品",
                    "大类": "配件",
                    "类目": "测试品类",
                    "近7天销量": "0",
                    "近7天销售额": "0",
                    "近30天销量": "0",
                    "库存": "0",
                    "场景主题": "测试场景",
                    "选品角色": "补充品类",
                    "活动匹配度": "0",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["AI选品分"], "5.00")
        self.assertEqual(result.output_rows[0]["推荐优先级"], "低")

    def test_process_rejects_invalid_activity_fit(self) -> None:
        with self.assertRaises(ValidationError):
            ai_selection.process(
                [
                    {
                        "项目": "安踏儿童",
                        "平台": "美团",
                        "款号": "312635583",
                        "商品名称": "UFO8男大童跑步系列秋季跑鞋",
                        "大类": "鞋类",
                        "类目": "跑步鞋",
                        "近7天销量": "52",
                        "近7天销售额": "20221.14",
                        "近30天销量": "212",
                        "库存": "180",
                        "场景主题": "暑期出行穿搭",
                        "选品角色": "核心推荐",
                        "活动匹配度": "101",
                    }
                ]
            )


class CopyContentProcessorTests(unittest.TestCase):
    def test_process_generates_copy_and_passes_check(self) -> None:
        result = copy_content.process(
            [
                {
                    "品牌": "安踏",
                    "平台": "天猫",
                    "内容类型": "商品短文案",
                    "商品名称": "轻量跑鞋",
                    "核心卖点": "轻量缓震/透气网面/适合日常跑步",
                    "目标人群": "年轻运动人群",
                    "活动利益点": "限时满500减80",
                    "品牌调性": "专业活力",
                    "禁用词": "最强,第一,绝对",
                    "内容主题": "开学运动季",
                    "开场文案": "新学期动起来，选对跑鞋很重要！",
                    "使用场景": "日常跑步、体育课和校园活动",
                    "品牌背书": "专业儿童运动品牌，陪孩子自在奔跑！",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["AI标题建议"], "开学运动季｜安踏轻量跑鞋")
        self.assertIn("新学期动起来，选对跑鞋很重要！", result.output_rows[0]["AI正文建议"])
        self.assertNotIn("整体表达保持", result.output_rows[0]["AI正文建议"])
        self.assertEqual(result.output_rows[0]["合规状态"], "通过")

    def test_process_flags_forbidden_word(self) -> None:
        result = copy_content.process(
            [
                {
                    "品牌": "安踏",
                    "平台": "天猫",
                    "内容类型": "商品短文案",
                    "商品名称": "轻量跑鞋",
                    "核心卖点": "最强缓震",
                    "目标人群": "年轻运动人群",
                    "活动利益点": "限时满500减80",
                    "品牌调性": "专业活力",
                    "禁用词": "最强,第一,绝对",
                    "内容主题": "开学运动季",
                    "开场文案": "新学期动起来，选对跑鞋很重要！",
                    "使用场景": "日常跑步、体育课和校园活动",
                    "品牌背书": "专业儿童运动品牌，陪孩子自在奔跑！",
                }
            ]
        )
        self.assertEqual(result.output_rows[0]["合规状态"], "需修改")
        self.assertEqual(result.output_rows[0]["命中禁用词"], "最强")

    def test_process_rejects_empty_selling_points(self) -> None:
        with self.assertRaises(ValidationError):
            copy_content.process(
                [
                    {
                        "品牌": "安踏",
                        "平台": "天猫",
                        "内容类型": "商品短文案",
                        "商品名称": "轻量跑鞋",
                        "核心卖点": "",
                        "目标人群": "年轻运动人群",
                        "活动利益点": "限时满500减80",
                        "品牌调性": "专业活力",
                        "禁用词": "最强,第一,绝对",
                        "内容主题": "开学运动季",
                        "开场文案": "新学期动起来，选对跑鞋很重要！",
                        "使用场景": "日常跑步、体育课和校园活动",
                        "品牌背书": "专业儿童运动品牌，陪孩子自在奔跑！",
                    }
                ]
            )

    def test_process_generates_publishable_anta_children_copy(self) -> None:
        result = copy_content.process(
            [
                {
                    "品牌": "安踏儿童",
                    "平台": "美团",
                    "内容类型": "商品种草文案",
                    "商品名称": "【UFO8】秋季男大童跑鞋",
                    "核心卖点": "轻弹缓震鞋底，跑跳自如不累脚；网面鞋身透气不闷汗，孩子穿一整天都干爽/后跟稳固支撑，护住脚踝，适合活泼好动的大男孩",
                    "目标人群": "男大童及其家长",
                    "活动利益点": "活动优惠待店铺更新，敬请关注～",
                    "品牌调性": "专业、活力、亲切",
                    "禁用词": "最强,第一,绝对,国家级,顶级,万能",
                    "内容主题": "宝贝开学季",
                    "开场文案": "宝贝开学季，运动量猛增，选对跑鞋太重要啦！👟",
                    "使用场景": "日常跑步、体育课、校园活动",
                    "品牌背书": "家长放心选，孩子自在跑——专业儿童运动品牌，活力满满过秋天！",
                }
            ]
        )

        expected_body = (
            "宝贝开学季，运动量猛增，选对跑鞋太重要啦！👟\n"
            "安踏儿童【UFO8】秋季男大童跑鞋，专为日常跑步、体育课、校园活动设计。\n"
            "轻弹缓震鞋底，跑跳自如不累脚；网面鞋身透气不闷汗，孩子穿一整天都干爽。\n"
            "后跟稳固支撑，护住脚踝，适合活泼好动的大男孩。\n"
            "家长放心选，孩子自在跑——专业儿童运动品牌，活力满满过秋天！\n"
            "（活动优惠待店铺更新，敬请关注～）"
        )
        self.assertEqual(result.output_rows[0]["AI标题建议"], "宝贝开学季｜安踏儿童【UFO8】秋季男大童跑鞋")
        self.assertEqual(result.output_rows[0]["AI正文建议"], expected_body)
        self.assertEqual(result.output_rows[0]["合规状态"], "通过")


if __name__ == "__main__":
    unittest.main()
