from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class DailyTask:
    day_index: int
    title: str
    business_action: str
    developer_action: str
    deliverable: str
    acceptance: str

    def __post_init__(self) -> None:
        if not isinstance(self.day_index, int):
            raise TypeError("day_index must be int")
        if self.day_index not in range(1, 6):
            raise ValueError("day_index must be between 1 and 5")
        for value in (self.title, self.business_action, self.developer_action, self.deliverable, self.acceptance):
            if not isinstance(value, str):
                raise TypeError("daily task text fields must be str")
            if not value.strip():
                raise ValueError("daily task text fields must not be empty")


@dataclass(frozen=True)
class RoadmapWeek:
    week_number: int
    start_date: date
    end_date: date
    workstream: str
    objective: str
    dependency: str
    milestone: str
    tasks: tuple[DailyTask, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.week_number, int):
            raise TypeError("week_number must be int")
        if self.week_number <= 0:
            raise ValueError("week_number must be positive")
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise TypeError("start_date and end_date must be date")
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days != 4:
            raise ValueError("each roadmap week must contain five working days")
        for value in (self.workstream, self.objective, self.dependency, self.milestone):
            if not isinstance(value, str):
                raise TypeError("roadmap week text fields must be str")
            if not value.strip():
                raise ValueError("roadmap week text fields must not be empty")
        if len(self.tasks) != 5:
            raise ValueError("each roadmap week must have five daily tasks")
        if tuple(task.day_index for task in self.tasks) != (1, 2, 3, 4, 5):
            raise ValueError("daily tasks must be ordered from 1 to 5")


@dataclass(frozen=True)
class MaterialRequirement:
    workstream: str
    material: str
    business_action: str
    purpose: str
    due_date: date
    required: bool
    acceptance: str
    existing_state: str

    def __post_init__(self) -> None:
        for value in (
            self.workstream,
            self.material,
            self.business_action,
            self.purpose,
            self.acceptance,
            self.existing_state,
        ):
            if not isinstance(value, str):
                raise TypeError("material text fields must be str")
            if not value.strip():
                raise ValueError("material text fields must not be empty")
        if not isinstance(self.due_date, date):
            raise TypeError("due_date must be date")
        if not isinstance(self.required, bool):
            raise TypeError("required must be bool")


@dataclass(frozen=True)
class CapabilityStatus:
    area: str
    capability: str
    status: str
    evidence: str
    next_action: str

    def __post_init__(self) -> None:
        for value in (self.area, self.capability, self.status, self.evidence, self.next_action):
            if not isinstance(value, str):
                raise TypeError("capability fields must be str")
            if not value.strip():
                raise ValueError("capability fields must not be empty")
        if self.status not in {"已有基础", "需补强", "待开发"}:
            raise ValueError("unsupported capability status")


def _task(
    day_index: int,
    title: str,
    business_action: str,
    developer_action: str,
    deliverable: str,
    acceptance: str,
) -> DailyTask:
    result = DailyTask(day_index, title, business_action, developer_action, deliverable, acceptance)
    assert result.title.strip()
    return result


ROADMAP_WEEKS = (
    RoadmapWeek(
        1,
        date(2026, 7, 27),
        date(2026, 7, 31),
        "数据处理",
        "冻结范围、字段口径和验收基线",
        "安踏现有周报/月报源文件与人工成品可读取",
        "需求、指标、文件和验收口径形成可签字版本",
        (
            _task(1, "确认一期范围", "确认一期先做安踏日报、周报和P2试点，不新增临时需求。", "把两条流水线、页面入口和不做事项写成范围清单。", "一期范围清单", "业务负责人确认范围且无模糊项目。"),
            _task(2, "盘点源文件", "按平台列出美团、京东、商品主数据及历史报表文件。", "扫描工作表、表头、日期和数据量，建立源文件清单。", "数据源清单", "每类文件都有样例、负责人和更新频率。"),
            _task(3, "确认指标口径", "确认销售额、销量、订单数、客单价、退款等主口径。", "把指标公式、字段来源和缺失处理写入指标字典。", "指标口径表", "每个核心指标都能追溯到源字段和公式。"),
            _task(4, "确认输出样式", "标记人工日报/周报中必须保留的页面和表格。", "拆解固定模板、图表、文字区和交付文件结构。", "报表结构确认稿", "业务能指出最终交付包中每个文件的用途。"),
            _task(5, "建立验收基线", "提供一份已确认正确的历史报表及对应源文件。", "形成逐指标对账表和测试用例清单。", "验收基线包", "核心指标可人工复算，历史数字不被当成当期源数据。"),
        ),
    ),
    RoadmapWeek(
        2,
        date(2026, 8, 3),
        date(2026, 8, 7),
        "数据处理",
        "完成文件识别、校验和阻断机制",
        "第1周源文件清单和指标口径已确认",
        "错误文件不能进入计算，系统可输出数据质量报告",
        (
            _task(1, "文件自动识别", "用标准命名上传3类真实文件。", "按文件名、工作表和表头识别品牌、平台、周期和资料类型。", "文件识别结果", "正确文件识别率达到试点样例100%，未知文件进入待确认。"),
            _task(2, "结构校验", "确认哪些工作表和字段属于必填。", "校验文件可读、工作表存在、必填字段非空。", "结构校验规则", "缺字段时页面明确显示字段名和修复方式。"),
            _task(3, "数据校验", "确认日期、订单状态、金额和数量的合法范围。", "实现日期、数值、空值、重复和周期越界检查。", "数据异常清单", "异常行可定位到源文件、工作表和行号。"),
            _task(4, "阻断与警告", "确认哪些问题必须停止、哪些可带警告继续。", "实现通过、警告、阻断三级结果。", "数据质量报告", "阻断数据不生成正式报表，警告必须随交付展示。"),
            _task(5, "真实文件回归", "补充至少1个错误样例和1个正确样例。", "用安踏7月文件完成正常、边界和异常测试。", "第2周测试报告", "正确样例通过，错误样例按预期阻断且不产生脏数据。"),
        ),
    ),
    RoadmapWeek(
        3,
        date(2026, 8, 10),
        date(2026, 8, 14),
        "数据处理",
        "建立公共标准数据层和确定性计算引擎",
        "文件质量校验通过",
        "P1报表与P2选品可共用同一套清洗后事实数据",
        (
            _task(1, "订单事实表", "确认美团有效订单状态和订单唯一键。", "建立订单事实表，保留平台、门店、商品、金额、退款和配送字段。", "order_fact标准表", "订单合计与源表在确认口径下完全一致。"),
            _task(2, "商品事实表", "确认京东商品指标和周期字段。", "建立商品日事实表并统一SKU、款号、类目和门店覆盖。", "product_day_fact标准表", "京东销量和销售额可按日、周、商品复算。"),
            _task(3, "商品主数据", "确认款号、库存、季节、科技和人群字段。", "建立商品主数据表及跨平台商品映射。", "product_master标准表", "试点商品匹配率有统计，未匹配项不被静默丢弃。"),
            _task(4, "指标计算引擎", "确认主KPI与保留小数规则。", "使用确定性程序计算金额、数量、占比、排名和环比。", "计算结果JSON", "AI不参与数字计算，金额采用Decimal且可重复运行。"),
            _task(5, "对账与留痕", "复核系统合计与人工基线差异。", "输出源表合计、标准层合计、指标合计和差异原因。", "三层对账报告", "所有差异为0或有已确认的口径解释。"),
        ),
    ),
    RoadmapWeek(
        4,
        date(2026, 8, 17),
        date(2026, 8, 21),
        "数据处理",
        "完成安踏日报自动化闭环",
        "标准数据层和指标引擎通过对账",
        "业务上传昨日文件后可获得可审核的日报交付包",
        (
            _task(1, "日报周期与对比", "确认日报截止时间、前一日和上周同日比较规则。", "实现昨日周期、前日和上周同日数据选择。", "日报周期结果", "跨月、周一和缺少上期数据时结果正确。"),
            _task(2, "日报指标与拆分", "确认平台、商品、门店、城市的展示顺序。", "计算核心指标、平台结构和TOP/后排明细。", "日报指标明细", "页面数字与计算JSON一致且可下载。"),
            _task(3, "日报异常诊断", "确认销售、退款、配送和低库存阈值。", "用规则引擎定位异常平台、商品、门店和城市。", "异常诊断清单", "每条异常包含证据数字和来源，不输出猜测原因。"),
            _task(4, "日报页面与导出", "选择Excel、网页或PDF中的正式交付组合。", "组装指标卡、趋势、异常和数据完整度。", "日报看板与交付包", "交付包包含源文件、质量报告、标准数据、指标和版本信息。"),
            _task(5, "日报业务验收", "按真实工作流程上传、检查并填写反馈。", "修复口径和页面问题，锁定日报1.0。", "日报UAT报告", "业务连续2个样例完成生成且核心指标对账通过。"),
        ),
    ),
    RoadmapWeek(
        5,
        date(2026, 8, 24),
        date(2026, 8, 28),
        "数据处理",
        "完成安踏周报、AI解读、审核和历史版本",
        "日报标准数据可用，周报源文件周期完整",
        "从上传到周报确认版形成一条可追溯流水线",
        (
            _task(1, "周报汇总", "确认自然周或品牌周定义。", "汇总7天标准数据并校验本周、上周口径一致。", "周报基础指标", "缺天、跨周期或口径不一致时停止比较。"),
            _task(2, "结构与贡献拆解", "确认平台、类目、商品、门店和城市关注顺序。", "计算周环比、贡献率、TOP商品和主要拖累。", "周报诊断JSON", "每个主要原因都有量化贡献，残差单独展示。"),
            _task(3, "AI分析初稿", "补充本周已确认业务事件。", "只向模型提供计算JSON、异常和确认事件，生成摘要与行动建议。", "AI周报初稿", "文字中的每个数字都能在计算结果中找到。"),
            _task(4, "审核与版本", "指定周报确认人和退回规则。", "完成数字质检、结论质检、人工确认和版本锁定。", "审核记录与历史版本", "修改生成新版本，不覆盖源文件和已确认版本。"),
            _task(5, "数据处理一期上线", "完成整周试运行并签署验收结果。", "修复问题、整理操作说明和备份方式。", "P1数据处理1.0", "业务可独立完成上传、查看质量报告、确认和下载。"),
        ),
    ),
    RoadmapWeek(
        6,
        date(2026, 8, 31),
        date(2026, 9, 4),
        "AI智能Brief",
        "建立P2任务、商品池和品牌事实资料入口",
        "P1公共商品主数据可复用，百炼API已提供",
        "资料不完整时明确阻断，完整时形成标准任务JSON",
        (
            _task(1, "新建内容任务", "选择项目、渠道、内容类型、目标和交付日期。", "建立P2任务表单、任务编号和状态流转。", "内容任务单", "同一任务可保存、继续编辑并查看负责人。"),
            _task(2, "商品池接入", "确认候选商品范围和可用库存。", "复用P1商品事实与主数据，建立候选商品池。", "商品池与素材索引", "商品事实来源、更新时间和缺失字段清楚可见。"),
            _task(3, "品牌资料结构化", "填写品牌调性、目标人群、禁用词和审核要求。", "把非标准文档整理为品牌规则和选项库。", "品牌规则JSON", "每条规则有品牌、适用渠道、版本和确认人。"),
            _task(4, "活动与平台规格", "提供确认后的主题、优惠、时间和尺寸规格。", "建立活动事实、平台字数、画布尺寸和CTA约束。", "活动与平台配置", "未确认优惠不得进入文案和Brief。"),
            _task(5, "完整度闸门", "补齐页面标红的必填资料。", "实现商品、品牌、活动和素材完整度检查。", "P2资料质量报告", "缺少事实字段时停止生成并精确提示补什么。"),
        ),
    ),
    RoadmapWeek(
        7,
        date(2026, 9, 7),
        date(2026, 9, 11),
        "AI智能Brief",
        "完成选品、场景和卖点证据链",
        "P2任务JSON和资料质量报告通过",
        "选品及卖点结论都可回溯到商品事实",
        (
            _task(1, "选品规则评分", "确认销量、库存、季节、活动匹配等权重。", "程序计算评分、风险和推荐角色。", "AI选品结果", "分数可复算，低库存和数据不足商品有风险标记。"),
            _task(2, "人群与场景策略", "确认目标人群、使用场景和传播方向。", "模型基于已确认人群和场景生成策略，不引入外部事实。", "人群场景JSON", "策略不超出品牌、商品和活动资料范围。"),
            _task(3, "卖点提炼", "确认材质、科技、功能和适用人群证明。", "将商品特征映射为用户利益和证据ID。", "卖点证据表", "每个卖点包含feature、benefit和source_id。"),
            _task(4, "Agent编排", "查看选品、场景、卖点三个节点结果。", "用统一任务JSON串联节点，记录输入输出与重跑版本。", "P2节点流水线", "任一节点失败可单独重跑，不重复生成整条任务。"),
            _task(5, "业务决策确认", "确认入选商品、主场景和核心卖点。", "锁定确认项，未确认项保留待办状态。", "Brief事实底稿", "后续文案与视觉只读取锁定底稿。"),
        ),
    ),
    RoadmapWeek(
        8,
        date(2026, 9, 14),
        date(2026, 9, 18),
        "AI智能Brief",
        "完成文案、视觉Brief和HTML Demo",
        "Brief事实底稿已由业务确认",
        "生成多版本文案和设计可直接执行的结构化Brief",
        (
            _task(1, "文案任务模板", "选择渠道、字数、语气、版本数和CTA。", "建立社群、短彩信、页面文案的结构化提示模板。", "文案任务JSON", "相同输入可稳定生成规定格式，不混用渠道规则。"),
            _task(2, "文案生成", "选择需要保留的版本并标记修改意见。", "调用文本模型生成标题、短句、正文和CTA多版本。", "多版本文案", "不编造折扣、材质、功效或品牌背书。"),
            _task(3, "视觉Brief", "确认画布尺寸、必放素材、版式偏好和禁用风格。", "生成层级、版式、素材清单、色彩方向和文案位置。", "结构化视觉Brief", "设计能仅凭Brief找到所需素材并完成首稿。"),
            _task(4, "HTML Demo与图片方案", "确认是否需要图片生成以及可用品牌素材范围。", "生成可预览HTML Demo；图片生成仅作为可选草图。", "HTML Demo或图片Prompt", "真实商品图不被AI伪造，草图明确标记不可直接发布。"),
            _task(5, "首轮业务评审", "按准确性、品牌感、可执行性逐项打分。", "汇总修改意见并更新模板版本。", "P2首轮评审报告", "至少3个安踏真实任务完成评审并记录问题类型。"),
        ),
    ),
    RoadmapWeek(
        9,
        date(2026, 9, 21),
        date(2026, 9, 25),
        "AI智能Brief",
        "补齐API、质检、人工确认和完整交付包",
        "文案与视觉Brief可稳定生成",
        "P2任务可审、可退回、可导出、可追溯",
        (
            _task(1, "模型API正式接入", "在本机管理员页录入并测试API Key。", "在服务端调用百炼兼容接口，密钥不写入Excel和浏览器。", "可用模型连接", "密钥不出现在页面源码、日志、导出文件中。"),
            _task(2, "事实与数字质检", "确认哪些风险必须阻断。", "校验模型输出中的商品、数字、优惠和证据ID。", "事实质检报告", "不存在来源的事实被阻断或标记待确认。"),
            _task(3, "品牌与合规质检", "确认禁用词、敏感表达和法务审核范围。", "执行禁用词、语气、长度和渠道规则检查。", "内容质检报告", "命中风险可定位到具体句子和规则。"),
            _task(4, "人工审核工作流", "审核通过、退回或修改，并填写原因。", "保存审核人、时间、意见和最终确认版本。", "审核记录", "未经确认的内容不能进入正式交付包。"),
            _task(5, "完整交付包", "确认文案、Brief、Demo和质检报告是否齐全。", "打包任务JSON、文案、Brief、Demo、质检和历史版本。", "P2完整交付包", "同一任务可下载完整包并重现生成过程。"),
        ),
    ),
    RoadmapWeek(
        10,
        date(2026, 9, 28),
        date(2026, 10, 2),
        "联调上线",
        "完成P1/P2联调、多人试用和交接",
        "两条流水线均通过模块验收",
        "组内业务可在局域网登录、保存数据并独立完成试点任务",
        (
            _task(1, "公共数据中心联调", "确认P1数据可被P2选品直接选择。", "打通标准数据、商品池和数据字典版本。", "P1/P2共用数据链路", "P2不重复上传已存在的商品事实数据。"),
            _task(2, "账号与权限", "提供试点用户姓名、账号和角色。", "配置管理员、业务提交人和审核人权限。", "试点账号清单", "不同角色只能看到和操作授权范围。"),
            _task(3, "多人并发与恢复", "安排3至5名业务同时完成真实任务。", "测试并发上传、保存、导出、重试和异常恢复。", "联调测试报告", "失败任务不污染数据，重复提交不会重复入库。"),
            _task(4, "培训与SOP", "按说明独立操作并记录不理解的步骤。", "整理一页操作清单、常见问题、备份和恢复步骤。", "业务操作SOP", "零开发基础用户可在指导下独立完成全流程。"),
            _task(5, "试点上线", "签署试点结果并登记后续迭代需求。", "发布局域网版本、锁定代码与数据备份。", "试点上线版本", "P1与P2各完成至少2个真实任务，问题有负责人和期限。"),
        ),
    ),
)


MATERIAL_REQUIREMENTS = (
    MaterialRequirement("数据处理", "美团订单/商品原始数据", "提供连续2周及1个异常样例，不手工改列名。", "订单、销售、退款、门店与配送计算", date(2026, 7, 28), True, "文件可打开，日期和平台明确，保留原始表头。", "已有多周安踏样例，需补异常样例。"),
    MaterialRequirement("数据处理", "京东商品分析原始数据", "提供与美团相同周期的连续2周文件。", "京东商品、类目、门店覆盖和周环比", date(2026, 7, 28), True, "数据工作表可识别，统计周期完整。", "已有多周安踏样例。"),
    MaterialRequirement("数据处理", "商品主数据/商品下载表", "提供款号、库存、季节、科技、人群和上市时间。", "商品映射、库存风险与P2选品复用", date(2026, 7, 29), True, "SKU/款号按文本保存，字段含义有说明。", "已有安踏商品下载样例。"),
    MaterialRequirement("数据处理", "指标口径确认表", "由业务负责人确认主销售额、有效订单、退款和客单价口径。", "确定性计算与对账", date(2026, 7, 30), True, "每个指标有公式、字段来源、负责人和生效日期。", "有标准模板，关键口径待确认。"),
    MaterialRequirement("数据处理", "正确人工报表与对应源文件", "选择1份确认正确的日报和2份连续周报。", "建立验收基线", date(2026, 7, 31), True, "人工报表周期与源文件完全对应。", "周报资料充足，正式日报样例缺失。"),
    MaterialRequirement("数据处理", "异常阈值与审核人", "确认销售下降、退款、配送、低库存阈值和最终确认人。", "异常诊断与人工确认", date(2026, 8, 18), True, "每条阈值有品牌、适用范围和确认人。", "尚待业务确认。"),
    MaterialRequirement("AI智能Brief", "品牌调性与品牌规范", "按标准模板选择语气、句式、禁用风格和必须表达。", "品牌规则库", date(2026, 9, 1), True, "规则可选择、可版本化，不只提供散文式说明。", "已有模板，需安踏最终确认版。"),
    MaterialRequirement("AI智能Brief", "商品事实与卖点证明", "提供商品名称、材质、科技、功能、人群及证明来源。", "卖点提炼与事实质检", date(2026, 9, 2), True, "每个卖点能对应商品字段、说明书或已确认资料。", "已有部分商品资料，证明来源需补。"),
    MaterialRequirement("AI智能Brief", "商品主图与细节图", "按商品ID命名，主图、侧面、细节和Logo分开存放。", "视觉Brief和素材索引", date(2026, 9, 2), True, "图片清晰、无过期活动字样、授权范围明确。", "需整理可用图片与授权范围。"),
    MaterialRequirement("AI智能Brief", "目标人群与使用场景", "从模板中选择主次人群、场景、痛点和购买动机。", "人群场景策略", date(2026, 9, 3), True, "场景与商品事实一致，不引入无法证明的功效。", "已有通用描述，需结构化确认。"),
    MaterialRequirement("AI智能Brief", "活动事实与优惠信息", "填写活动主题、时间、优惠、适用范围和确认状态。", "文案CTA与活动一致性", date(2026, 9, 3), True, "未确认优惠明确标记待确认。", "需按具体任务提供。"),
    MaterialRequirement("AI智能Brief", "禁用词与合规规则", "提供品牌禁用词、平台敏感词和必须人工审核的表达。", "内容质量检查", date(2026, 9, 4), True, "每条规则有风险等级和替代表达。", "已有标准模板，需业务/法务确认。"),
    MaterialRequirement("AI智能Brief", "平台规格", "提供各渠道字数、图片尺寸、CTA和必放元素。", "文案和视觉Brief格式控制", date(2026, 9, 4), True, "规格包含平台、内容位、尺寸/字数和更新时间。", "尚待收集。"),
    MaterialRequirement("AI智能Brief", "历史优秀与失败案例", "各提供至少5个，并说明好或不好的原因。", "模型风格参考与评审标准", date(2026, 9, 8), False, "案例属于同品牌同渠道，旧优惠仅作风格参考。", "已有部分历史文案，失败案例不足。"),
    MaterialRequirement("联调上线", "试点用户与权限表", "提供3至5名用户、角色、品牌和审核关系。", "登录、数据保存和审核权限", date(2026, 9, 28), True, "账号不重复，审核人与提交人关系明确。", "需试点前提供。"),
)


CAPABILITY_STATUSES = (
    CapabilityStatus("公共基础", "登录、局域网访问、数据保存", "已有基础", "现有工作台使用SQLite保存账号、会话和处理记录。", "补充角色权限、并发和备份恢复测试。"),
    CapabilityStatus("公共基础", "资料投递、索引和数据字典", "已有基础", "网页可上传并更新本地资料索引与数据字典。", "增加版本、质量状态和事实表关联。"),
    CapabilityStatus("数据处理", "安踏周报/月报指标初稿", "已有基础", "可读取现有安踏源文件并输出CSV初稿。", "升级为标准数据层、对账、日报和完整交付包。"),
    CapabilityStatus("数据处理", "日报与质量阻断", "待开发", "当前没有正式安踏日报样例和完整质量流水线。", "按第1至4周完成。"),
    CapabilityStatus("数据处理", "标准事实表与历史版本", "待开发", "现有数据库尚未保存订单事实、商品事实和商品主数据。", "按第2、3、5周完成。"),
    CapabilityStatus("AI智能Brief", "规则选品", "已有基础", "已有安踏/通用项目选择及规则评分。", "改为读取公共商品数据并保存权重版本。"),
    CapabilityStatus("AI智能Brief", "文案生成与百炼接口", "需补强", "已有文案入口、基础生成和API配置页。", "改为事实底稿驱动的结构化多版本生成。"),
    CapabilityStatus("AI智能Brief", "人群场景、卖点证据链", "待开发", "尚未形成独立节点和source_id证据。", "按第7周完成。"),
    CapabilityStatus("AI智能Brief", "视觉Brief与HTML Demo", "待开发", "当前没有结构化视觉Brief及成图/HTML节点。", "按第8周完成。"),
    CapabilityStatus("AI智能Brief", "质检、审核、交付包和历史版本", "待开发", "当前结果以单次CSV为主。", "按第9、10周完成。"),
)


def daily_task_date(week: RoadmapWeek, task: DailyTask) -> date:
    if not isinstance(week, RoadmapWeek):
        raise TypeError("week must be RoadmapWeek")
    if not isinstance(task, DailyTask):
        raise TypeError("task must be DailyTask")
    result = week.start_date + timedelta(days=task.day_index - 1)
    assert week.start_date <= result <= week.end_date
    return result


def roadmap_day_count() -> int:
    result = sum(len(week.tasks) for week in ROADMAP_WEEKS)
    assert result > 0
    return result


assert len(ROADMAP_WEEKS) == 10
assert roadmap_day_count() == 50
assert ROADMAP_WEEKS[0].start_date == date(2026, 7, 27)
assert ROADMAP_WEEKS[-1].end_date == date(2026, 10, 2)
