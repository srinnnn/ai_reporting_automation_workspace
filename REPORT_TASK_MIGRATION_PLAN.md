# REPORT_TASK_MIGRATION_PLAN

## 1. 当前日报流程

目标入口：

- `POST /anta-reporting/meituan-daily/run`
- 当前处理函数：`intranet_app/app.py::_handle_anta_meituan_reporting_run(..., "daily")`

### 输入

页面当前提交内容较轻：

- `report_date`：业务选择的日报日期，页面日期格式通常为 `YYYY-MM-DD`，后端会转换为紧凑日期 `YYYYMMDD`。
- 当前登录用户：从 session 中读取，用于保存 job 和导入记录的 `created_by/uploaded_by`。

当前代码内固定业务口径：

- 品牌：安踏儿童
- `brand_id`：`anta_kids`
- 平台：`meituan`
- 渠道：`instant_retail`
- 报表类型：`daily`

### 文件同步

当前日报入口会先执行：

```text
_sync_meituan_download_sources()
```

作用：

- 从美团插件导出目录和本地下载目录同步新增文件。
- 将可识别的美团报表文件复制到系统 intake/runtime 目录。
- 返回本次同步到的文件列表，用于日志和 source manifest。

### 基础层导入

文件同步后，当前日报入口继续执行：

```text
_ingest_meituan_plugin_files_to_foundation(user.username)
```

作用：

- 扫描已同步的美团导出文件。
- 按文件类型识别为：
  - `product_order`
  - `store_finance`
  - `store_traffic`
  - `service_review`
- 调用基础层识别、字段映射、清洗、校验和品牌匹配逻辑。
- 校验通过后写入统一基础事实表。

约束：

- 原始下载文件只能作为 intake 输入。
- 正式日报不能直接从原始 CSV/Excel 生成。
- 日报必须从统一基础数据层读取。

### 数据读取

当前日报入口通过：

```text
_load_anta_meituan_sources_from_foundation("daily", selected_report_date)
```

从基础数据层读取：

- `fact_order_product` 对应 `product_order`
- `fact_store_finance` 对应 `store_finance`
- `fact_store_traffic` 对应 `store_traffic`
- `fact_service_review` 对应 `service_review`

读取结果会组装为 `anta_meituan_reporting.MeituanReportSources`。

日报核心要求：

- `product_order` 是必需数据。
- 日报日期以商品订单数据的选中日期为主。
- 门店 TOP、商品 TOP、近 7 天相关指标需要基础层内有足够日期窗口数据。

### 报表生成

当前日报生成调用：

```text
anta_meituan_reporting.build_meituan_daily_report(
    sources,
    selected_files["product"].end_date,
)
```

输出：

- `ProcessingResult.module`
- `ProcessingResult.output_rows`
- `ProcessingResult.summary`
- `ProcessingResult.warnings`

### 文件保存

当前同步流程会继续在 `app.py` 内完成：

```text
write_csv(result_path, result.output_rows)
storage.save_job(...)
_result_page(...)
```

当前保存资产：

- `result_path`：日报结果 CSV。
- `source_manifest_path`：本次使用的基础层来源说明 JSON。
- `job_id`：用于 `/jobs/{job_id}/download` 下载。

当前问题：

- 文件同步、入库、基础层读取、报表生成、结果保存都在一个 Web 请求线程内完成。
- 如果美团文件较多、基础层导入较慢或日报计算失败，用户只能等待请求结束。
- 失败原因没有形成统一任务状态，难以做管理页监控。

## 2. Task 化目标流程

目标链路：

```text
页面
↓
TaskSubmitter
↓
REPORT_GENERATE
↓
TaskRequest
↓
TaskRunner
↓
ReportExecutor
↓
ReportService
↓
FoundationRepository
↓
anta_meituan_reporting
↓
TaskResult
↓
TaskQueryService
```

### 目标职责划分

页面层：

- 读取表单日期。
- 构造任务 payload。
- 调用 `TaskSubmitter.submit(...)`。
- 根据返回的 `TaskResult` 或 task_id 展示结果、失败原因或任务状态。

`TaskSubmitter`：

- 校验 `task_type` 和 payload。
- 调用 `TaskService.create_task(...)` 创建任务记录。
- 构造 `TaskRequest`。
- 调用 `TaskRunner.run(...)`。
- 调用 `TaskService.save_task_result(...)` 保存任务结果。

`TaskRunner`：

- 按 `TaskType.REPORT_GENERATE` 选择 `ReportExecutor`。
- 不包含业务逻辑。
- 不访问数据库。

`ReportExecutor`：

- 从 payload 组装 `MeituanReportRequest`。
- 调用 `ReportService.build_meituan_daily_report(...)`。
- 将 `ProcessingResult` 摘要包装为 `TaskResult`。

`ReportService`：

- 通过 `FoundationRepository` 读取基础层。
- 调用现有 `anta_meituan_reporting.build_meituan_daily_report(...)`。
- 保持日报计算口径不变。

`TaskQueryService`：

- 提供任务状态、失败原因、结果摘要给管理页或未来状态页。

### 重要边界

第一版迁移不应该把“美团文件同步”和“基础层导入”强行塞进 `ReportExecutor`。

原因：

- `ReportExecutor` 的职责是报表生成，不应同时负责原始文件同步和数据入库。
- 数据导入应该属于 `DATA_IMPORT`。
- 日报生成应该只依赖已经清洗后的基础层。

因此日报 Task 化有两个可选模式：

#### 模式 A：严格任务拆分

```text
页面点击生成日报
↓
先触发 DATA_IMPORT 同步/入库任务
↓
确认基础层就绪
↓
再触发 REPORT_GENERATE 任务
```

优点：

- 架构最清晰。
- 数据导入和报表生成边界明确。
- 未来接 Celery 后可以拆成任务链。

缺点：

- 页面需要展示两个阶段状态。
- 初期改造成本较高。

#### 模式 B：日报入口先保持同步预处理，再任务化报表生成

```text
页面点击生成日报
↓
app.py 暂时保留美团文件同步和基础层导入
↓
TaskSubmitter.submit(REPORT_GENERATE, payload, user)
↓
ReportExecutor / ReportService 从基础层生成日报
```

优点：

- 改造风险低。
- 结果页面可以保持接近旧体验。
- 适合第一阶段灰度。

缺点：

- Web 请求线程里仍有同步文件导入。
- 不是最终异步形态。

建议：

- 第一阶段采用模式 B。
- 第二阶段再把同步/入库前置逻辑拆为 `DATA_IMPORT`。

## 3. Payload 设计

### 第一阶段日报任务输入 JSON

用于 `TaskSubmitter.submit(TaskType.REPORT_GENERATE, payload, created_by)`。

```json
{
  "task_name": "安踏儿童美团日报-20260725",
  "business_unit": "anta_retail_team",
  "brand_id": "anta_kids",
  "brand_name": "安踏儿童",
  "brand": "安踏儿童",
  "platform": "meituan",
  "channel": "instant_retail",
  "report_type": "daily",
  "report_period": "daily",
  "date": "20260725",
  "report_date": "20260725",
  "date_window": "20260725",
  "output_folder": "runtime/results",
  "frequency": "daily",
  "scheduled_time": "09:30",
  "source_policy": "foundation_only"
}
```

### 字段说明

- `task_name`
  - 管理页展示名称。
  - 建议格式：`品牌 + 平台 + 报表类型 + 日期`。

- `business_unit`
  - 业务组或项目归属。
  - 用于未来权限隔离和任务筛选。

- `brand_id`
  - 系统内部品牌 ID。
  - 日报正式取数必须用它过滤基础层。

- `brand_name` / `brand`
  - 页面展示品牌名。
  - `brand_name` 用于系统字段，`brand` 用于满足业务阅读和后续兼容。

- `platform`
  - 平台标识，安踏美团日报固定为 `meituan`。

- `channel`
  - 渠道标识，安踏即时零售固定为 `instant_retail`。

- `report_type`
  - 业务报表类型，日报为 `daily`。

- `report_period`
  - 当前 `ReportExecutor` 识别字段，日报必须为 `daily`。

- `date`
  - 面向业务阅读的日期字段。

- `report_date`
  - 当前 `ReportExecutor` 需要的执行日期。
  - 格式：`YYYYMMDD`。

- `date_window`
  - 任务记录中的日期范围。
  - 日报为单日，如 `20260725`。

- `output_folder`
  - 结果输出目录。
  - 第一阶段可继续使用 `runtime/results`。

- `frequency`
  - 任务频率。
  - 日报固定为 `daily`。

- `scheduled_time`
  - 任务默认执行时间。
  - 手动触发时可作为记录字段，不代表真的定时。

- `source_policy`
  - 数据来源策略。
  - 必须为 `foundation_only`，用于提醒迁移时不能从原始文件直接生成正式日报。

### 禁止放入 payload 的内容

- 原始 CSV/Excel 全量行数据。
- API Key、账号密码、Cookie。
- 用户本地下载目录。
- 浏览器插件内部状态。
- 可绕过基础层的原始文件路径。

允许放入 payload 的文件引用：

- 已进入系统 intake 或上传目录、且只用于导入任务的文件路径。
- 对于 `REPORT_GENERATE`，不建议传文件路径；应只传品牌、平台、渠道、日期。

## 4. Result 设计

### 成功返回

目标 `TaskResult.result`：

```json
{
  "task_id": 123,
  "report_file": "runtime/results/20260725_anta_meituan_daily_report.csv",
  "source_manifest_file": "runtime/uploads/20260725_anta_meituan_daily_sources.json",
  "summary": {
    "report_type": "daily",
    "brand_id": "anta_kids",
    "brand_name": "安踏儿童",
    "platform": "meituan",
    "channel": "instant_retail",
    "report_date": "20260725",
    "output_row_count": "35",
    "warning_count": "0",
    "sales_amount": "103425",
    "top_store_count": "30",
    "top_product_count": "10"
  }
}
```

第一阶段与现有 `ReportExecutor` 的差异：

- 现有 `ReportExecutor` 已返回：
  - `module`
  - `output_row_count`
  - `warning_count`
  - `summary`
- 但还没有保存 `report_file`。
- 日报正式迁移时需要补一个“结果文件保存边界”，建议放在专门的结果资产服务或 route adapter 中，不直接塞进 `ReportService`。

### 失败返回

目标 `TaskResult.error` 可以采用结构化错误前缀：

```json
{
  "task_id": 123,
  "status": "failed",
  "error_code": "FOUNDATION_DATA_MISSING",
  "error_message": "基础数据层缺少 product_order，无法生成 20260725 安踏儿童美团日报。"
}
```

建议错误码：

- `INVALID_PAYLOAD`
  - 日期、品牌、平台、渠道缺失或格式错误。

- `FOUNDATION_DATA_MISSING`
  - 基础层缺少日报必需数据。

- `FOUNDATION_DATE_NOT_READY`
  - 基础层有数据，但没有目标日期数据。

- `REPORT_GENERATION_FAILED`
  - `anta_meituan_reporting` 计算失败。

- `RESULT_SAVE_FAILED`
  - 报表生成成功，但 CSV 或 source manifest 保存失败。

- `UNKNOWN_ERROR`
  - 未归类异常。

### 失败信息展示要求

页面不应只展示“生成失败”。

至少展示：

- task_id
- 日期
- 品牌
- 平台
- 缺失的数据类型
- 建议动作

示例：

```text
任务 123 失败：
安踏儿童 / 美团 / 20260725 日报无法生成。
缺少基础层数据：store_finance、store_traffic。
请先使用美团插件导出对应日期数据并执行数据入库。
```

## 5. 新旧结果一致性方案

目标：

同一天、同一基础层数据，新旧流程输出必须一致。

比较对象：

```text
旧流程：
POST /anta-reporting/meituan-daily/run
↓
app.py 同步流程直接生成 CSV

新流程：
TaskSubmitter.submit(REPORT_GENERATE, payload, user)
↓
ReportExecutor
↓
ReportService
↓
生成 CSV 或 TaskResult
```

### 测试日期范围

建议先使用已验证过的安踏美团日期：

- `20260725`
- 再扩展到 7 天窗口：`20260715` 到 `20260725` 中有基础层数据的日期。

### 比较维度

#### 1. 行数

比较：

- `len(old_result.output_rows)`
- `len(new_result.output_rows)`

必须一致。

#### 2. 金额

核心金额字段必须一致：

- 昨日销售额
- MTD 销售额
- YTD 销售额
- 门店 TOP 榜销售额
- 商品 TOP 榜销售额

金额比较规则：

- 使用 Decimal。
- 去除千分位、人民币符号和空格后比较。
- 不允许使用 float。

#### 3. 核心字段

至少比较：

- 报表类型
- 品牌
- 平台
- 渠道
- 报表日期
- 门店 TOP 榜名称和排序
- 商品 TOP 榜名称/SKU 和排序
- 快报文案板块
- warnings 数量和内容

#### 4. 文件内容

CSV 比较规则：

- 统一 UTF-8。
- 表头顺序必须一致。
- 行顺序必须一致。
- 空字符串和缺失字段不能被混用。

### Golden Case 流程

```text
准备同一批基础层数据
↓
运行旧日报流程，保存 old.csv
↓
运行 Task 化日报流程，保存 new.csv
↓
读取两个 CSV
↓
比较表头、行数、核心字段、金额字段
↓
输出 migration_diff_report.json
```

### 通过标准

必须满足：

- 表头一致。
- 行数一致。
- 核心金额一致。
- TOP 门店和 TOP 商品排序一致。
- summary 中核心指标一致。
- warnings 不少于旧流程。

允许差异：

- 文件名不同。
- source manifest 中 task_id、生成时间不同。
- 任务状态字段是新增信息，可以不和旧流程比较。

## 6. 灰度迁移方案

### 第一阶段：隐藏开关

目标：

- 不改变页面视觉和业务操作。
- 默认仍走旧同步流程。
- 允许开发者或管理员通过隐藏开关切到 Task 流程。

建议开关：

- 环境变量：`REPORT_TASK_MODE=legacy|task`
- 默认：`legacy`

第一阶段流程：

```text
if REPORT_TASK_MODE == "legacy":
    继续走当前 _handle_anta_meituan_reporting_run
else:
    走 TaskSubmitter + ReportExecutor + ReportService
```

验收：

- 旧模式完全不受影响。
- Task 模式下 `20260725` 日报结果和旧流程一致。
- 失败时能返回 task_id 和 error。

注意：

- 这个阶段仍然可以同步等待 TaskResult。
- 不需要新增轮询页面。
- 不接 Redis/Celery。

### 第二阶段：内部用户测试

目标：

- 面向内部管理者或开发同事开放 Task 流程。
- 记录真实使用中的失败原因和耗时。

建议策略：

- 管理员账号显示“任务模式生成日报”按钮。
- 普通用户继续使用旧按钮。
- 每次 Task 生成后写入任务记录，并允许从只读任务页查看状态。

内部测试指标：

- 成功率。
- 平均耗时。
- 失败原因分布。
- 新旧结果一致率。
- 用户是否能理解错误提示。

必须覆盖场景：

- 目标日期数据完整。
- 缺 `product_order`。
- 缺 `store_finance`。
- 缺 `store_traffic`。
- 缺 `service_review`。
- 基础层有多日期数据。
- 重复点击同一天日报。

### 第三阶段：正式切换

目标：

- 默认走 Task 流程。
- 保留旧流程作为紧急回滚。

正式切换条件：

- 连续 7 个可用日报日期新旧结果一致。
- 内部测试无 P0/P1 级别缺陷。
- 失败提示能明确告诉业务方下一步动作。
- 任务查询页能查到最近任务、失败原因和结果摘要。

切换后流程：

```text
页面点击生成日报
↓
TaskSubmitter.submit(REPORT_GENERATE, payload, user)
↓
同步返回 TaskResult 或 task_id
↓
页面展示结果或任务状态
```

回滚策略：

- 保留环境变量或配置项 `REPORT_TASK_MODE=legacy`。
- 出现重大问题时，切回旧同步流程。
- 不删除旧 `_handle_anta_meituan_reporting_run`，直到 Redis/Celery 和任务状态页稳定。

## 7. 迁移前置改造清单

虽然本阶段不改代码，但后续正式迁移前必须补齐以下事项：

1. 结果文件保存边界
   - 当前 `ReportExecutor` 只返回 `ProcessingResult` 摘要。
   - 日报页面还需要 CSV 文件和 job 下载入口。
   - 建议新增结果资产保存服务，而不是让 `ReportService` 负责文件 IO。

2. 缺失基础数据诊断
   - 当前 `ReportService` 对 `product_order` 缺失会 fail closed。
   - 需要扩展错误信息，明确缺哪类基础数据。

3. 新旧一致性测试
   - 先以 `20260725` 为 golden case。
   - 再覆盖近 7 天。

4. 任务状态页面
   - 至少能看到 task_id、任务类型、状态、提交人、提交时间、结果摘要、失败原因。

5. 重复提交策略
   - 同一用户、同一品牌、同一平台、同一日期重复提交时，需要明确是允许生成多个结果，还是复用最近成功结果。

## 8. 本阶段明确不做

- 不修改 `app.py`。
- 不修改任何路由。
- 不修改 `ReportService`。
- 不修改 `ReportExecutor`。
- 不修改 `TaskSubmitter`。
- 不修改 `TaskRunner`。
- 不修改 Repository。
- 不修改数据库 schema。
- 不接 Redis。
- 不接 Celery。
- 不改变现有日报页面行为。
