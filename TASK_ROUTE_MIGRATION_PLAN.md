# Task Route Migration Plan

## 1. 当前页面入口分析

本计划基于 `intranet_app/app.py` 当前路由结构整理，目标是后续把现有同步页面逐步迁移到任务系统。当前阶段只规划，不修改代码。

### 数据上传入口

- `GET /data-foundation`
  - 页面：数据入库中心。
  - 当前渲染函数：`_data_foundation_page(...)`。

- `POST /data-foundation/check`
  - 入口：业务上传 Excel/CSV 后进行数据识别、字段映射、校验和入库。
  - 当前处理函数：`_handle_data_foundation_check(...)`。

- `GET /archive-intake`
  - 页面：资料投递/归档入口。
  - 当前渲染函数：`_archive_intake_page(...)`。

- `POST /archive-intake/upload`
  - 入口：资料文件上传到待归档目录。
  - 当前处理函数：`_handle_archive_intake_upload(...)`。

- `POST /archive-intake/run`
  - 入口：执行资料归档和索引更新。
  - 当前处理函数：`_handle_archive_intake_run(...)`。

- `POST /scenario/{scenario_key}/run`
  - 入口：通用 Excel/CSV 上传处理，包括博西短彩信、AI 选品辅助、文案辅助等传统场景。
  - 当前处理函数：`_handle_run(...)`。

### 日报入口

- `GET /anta-reporting`
  - 页面：安踏报表入口。
  - 当前渲染函数：`_anta_reporting_page(...)`。

- `POST /anta-reporting/meituan-daily/run`
  - 入口：安踏美团日报生成。
  - 当前处理函数：`_handle_anta_meituan_reporting_run(..., "daily")`。

### 周报入口

- `POST /anta-reporting/meituan-weekly/run`
  - 入口：安踏美团周报生成。
  - 当前处理函数：`_handle_anta_meituan_reporting_run(..., "weekly")`。

- `POST /anta-reporting/weekly/run`
  - 入口：安踏历史周报初稿生成。
  - 当前处理函数：`_handle_anta_reporting_run(..., "weekly")`。

### AI 内容入口

- `GET /p2-content-center`
  - 页面：P2 内容生产中心。
  - 当前渲染函数：`_p2_content_center_page(...)`。

- `POST /p2-content-center/run`
  - 入口：P2 AI 内容生成。
  - 当前处理函数：`_handle_p2_content_center_run(...)`。

- `POST /scenario/ai_selection/run`
  - 入口：旧版 AI 选品辅助场景。
  - 当前处理函数：`_handle_run(...)` 调用 `PROCESSORS["ai_selection"]`。

- `POST /scenario/copy_content/run`
  - 入口：旧版文案内容辅助场景。
  - 当前处理函数：`_handle_run(...)` 调用 `PROCESSORS["copy_content"]`。

### 文件下载入口

- `GET /jobs/{job_id}/download`
  - 入口：下载处理结果 CSV。
  - 当前处理函数：`_download_job_result(...)`。

- `GET /development-roadmap/download`
  - 入口：下载开发排期 Excel。

- `GET /archive-index/download`
  - 入口：下载资料索引 CSV。

- `GET /data-dictionary/download`
  - 入口：下载数据字典 CSV。

- `GET /scenario/{scenario_key}/template`
  - 入口：下载场景模板文件。

## 2. 当前同步流程

### 数据入库：`POST /data-foundation/check`

当前流程：

```text
页面提交 multipart 表单和文件
↓
app.py 解析表单与上传文件
↓
read_table 读取 Excel/CSV
↓
storage 读取已知门店和商品编码
↓
build_ingestion_plan 执行识别、字段映射、清洗、校验、品牌匹配
↓
app.py 写入上传文件到 runtime/uploads/data_foundation
↓
storage.save_foundation_check 保存校验报告
↓
如 ready_for_import，则 storage.save_foundation_fact_rows 写入基础事实表
↓
返回数据入库结果页面
```

问题：

- HTTP 请求线程承担文件读取、清洗、校验和入库。
- 大文件或多用户并发时会阻塞页面响应。
- 当前直接在 `app.py` 编排 `data_foundation.py` 和 `storage.py`。

### 安踏美团日报/周报：`POST /anta-reporting/meituan-daily/run`、`POST /anta-reporting/meituan-weekly/run`

当前流程：

```text
页面提交日期或点击生成
↓
app.py 同步美团插件/下载目录文件
↓
app.py 将插件文件导入统一基础数据层
↓
app.py 从基础数据层读取 product_order / store_finance / store_traffic / service_review
↓
anta_meituan_reporting 生成日报或周报
↓
write_csv 写结果文件
↓
storage.save_job 保存 job 记录
↓
返回结果预览页面和下载入口
```

问题：

- 文件同步、基础层导入、报表生成、CSV 写入都在同一个请求内完成。
- 当前已经遵守“正式报表从基础数据层读取”的核心规则，但编排仍在 `app.py`。
- 当选定日期数据缺失时，用户需要等待同步和入库结束后才看到失败。

### 历史安踏周报/月报：`POST /anta-reporting/weekly/run`、`POST /anta-reporting/monthly/run`

当前流程：

```text
页面点击生成
↓
app.py 从本地资料目录查找历史周报/月报素材
↓
anta_reporting 生成初稿
↓
write_csv 写结果
↓
storage.save_job 保存 job
↓
返回结果预览页面和下载入口
```

问题：

- 这部分还没有完全基础层化。
- 迁移到任务系统前，应先确认是否继续保留为历史兼容入口，还是迁移为正式 P1 报表链路。

### P2 内容生产：`POST /p2-content-center/run`

当前流程：

```text
页面提交品牌、渠道、日期、任务类型、输出数量
↓
app.py 构造 P2ContentRequest
↓
app.py 同步美团插件/下载目录文件
↓
app.py 将插件文件导入统一基础数据层
↓
app.py 从基础数据层读取 product_order 和 service_review
↓
BailianClient 从环境变量读取百炼配置
↓
content_pipeline.build_p2_content_pack 生成选品、卖点、文案、视觉 Brief 和质检提示
↓
write_csv 写 P2 交付包
↓
storage.save_job 保存 job
↓
返回 P2 结果预览页面和下载入口
```

问题：

- AI 调用在 Web 请求线程内完成，慢响应和接口失败会直接影响页面体验。
- 当前已保证 P2 不直接读取原始下载文件，但 Service/Worker 尚未接入路由。
- API 403、网络超时、返回 JSON 异常需要更明确的任务失败状态。

### 通用场景上传：`POST /scenario/{scenario_key}/run`

当前流程：

```text
页面上传 Excel/CSV
↓
app.py read_table 读取文件
↓
PROCESSORS[scenario_key] 同步处理
↓
write_csv 写结果
↓
storage.save_job 保存 job
↓
返回结果预览页面和下载入口
```

问题：

- 仍是旧的同步处理器链路。
- 其中 P1/P2 正式能力不能直接沿用这个入口读取原始文件；只能用于历史工具、诊断工具或显式模板处理。

### 文件下载：`GET /jobs/{job_id}/download`

当前流程：

```text
页面点击下载
↓
storage.get_job 查询 job
↓
检查 result_file 是否存在
↓
_send_file 返回 CSV 文件
```

问题：

- 下载入口本身不重，迁移优先级低。
- 未来任务化后，需要兼容“任务结果文件”和旧 job 文件两种来源。

## 3. 未来任务化流程

目标链路：

```text
页面
↓
TaskSubmitter
↓
TaskService.create_task
↓
TaskRequest
↓
TaskRunner
↓
Executor
↓
Service
↓
Repository
↓
TaskResult
↓
TaskService.save_task_result
↓
TaskQueryService
↓
页面查询状态/结果
```

### 数据入库未来流程

```text
POST /data-foundation/check
↓
页面层只负责保存上传文件和构造 payload
↓
TaskSubmitter.submit(DATA_IMPORT, payload, user)
↓
DataImportExecutor
↓
DataFoundationService.process_rows
↓
FoundationRepository
↓
TaskResult(status/result/error)
↓
TaskQueryService 给页面读取状态
```

迁移约束：

- `DataImportExecutor` 只能调用 `DataFoundationService`。
- `DataFoundationService` 继续调用现有 `build_ingestion_plan`。
- 正式入库仍必须经过识别、字段映射、清洗、校验、品牌归属判断。

### 报表生成未来流程

```text
POST /anta-reporting/meituan-daily/run
↓
TaskSubmitter.submit(REPORT_GENERATE, payload, user)
↓
ReportExecutor
↓
ReportService.build_meituan_daily_report 或 build_meituan_weekly_report
↓
FoundationRepository 读取统一基础层
↓
anta_meituan_reporting 生成结果
↓
TaskResult
↓
TaskQueryService 返回状态、摘要、错误
```

迁移约束：

- 日报、周报正式输出必须继续从基础数据层读取。
- 不允许从 `Downloads`、`runtime/intake` 或原始文件直接生成正式报表。
- 报表结果文件保存和 `jobs` 下载兼容需要单独设计，不能在第一步迁移里混入大改。

### AI 内容未来流程

```text
POST /p2-content-center/run
↓
TaskSubmitter.submit(AI_CONTENT_GENERATE, payload, user)
↓
AIContentExecutor
↓
AIContentService.build_content_pack
↓
AIService
↓
ai_gateway.BailianClient
↓
content_pipeline.build_p2_content_pack
↓
TaskResult
↓
TaskQueryService 返回状态、摘要、错误
```

迁移约束：

- Prompt、输出字段和 AI 结果解析继续由 `content_pipeline.py` 负责。
- API Key 继续从环境变量读取，不写入 payload、日志、CSV 或浏览器代码。
- 失败状态必须区分：基础层缺数据、API 未配置、API 403、AI 返回 JSON 格式错误。

### 下载入口未来流程

```text
GET /jobs/{job_id}/download
↓
优先兼容旧 job 下载
↓
后续新增 task result download 查询
↓
根据 task_id 或 job_id 返回结果文件
```

建议：

- 下载入口不要优先迁移。
- 等报表和 AI 内容任务都能稳定保存结果文件后，再设计统一结果资产表或兼容查询层。

## 4. 迁移优先级

### P0：日报生成

入口：

- `POST /anta-reporting/meituan-daily/run`

原因：

- 日报是高频入口，用户每天使用。
- 当前链路包含同步插件文件、入库、基础层读取、报表生成和 CSV 写入，最容易阻塞请求。
- 报表已经有 `ReportService`、`ReportExecutor`、`TaskSubmitter`、`TaskQueryService` 基础组件，迁移条件最好。

建议步骤：

1. 不改变页面外观，只在后端分支中构造 `REPORT_GENERATE` payload。
2. 首次迁移仍使用本地同步 `TaskSubmitter`，返回结果页面保持不变。
3. 增加任务状态记录，失败时页面展示 task_id 和错误原因。
4. 验证 7 天内日报生成结果与旧链路完全一致。

### P1：AI 内容生成

入口：

- `POST /p2-content-center/run`

原因：

- AI 调用耗时和失败不稳定，最适合任务化。
- 当前已有 `AIService`、`AIContentService`、`AIContentExecutor`。

建议步骤：

1. 先迁移 P2 内容中心，不迁移旧 `scenario/copy_content/run`。
2. TaskResult 中保留候选商品数、输出条数、warning 数、API 错误。
3. 页面先同步等待结果，之后再升级为“提交后轮询状态”。

### P2：数据导入

入口：

- `POST /data-foundation/check`
- 插件同步后的自动入库逻辑。

原因：

- 入库是所有 P1/P2 的前置依赖，但上传页面需要处理文件内容，迁移时要谨慎。
- 当前 `DataFoundationService` 已可承接业务编排。

建议步骤：

1. 先迁移插件导入到 `DATA_IMPORT`，因为它已有固定目录和规则。
2. 再迁移手动上传数据入库。
3. 文件保存仍由页面层完成，payload 只传文件路径、metadata、sha256、必要行数据或后续文件引用。

### P3：其他任务

入口：

- `POST /scenario/{scenario_key}/run`
- `POST /archive-intake/run`
- `POST /archive-intake/upload`
- `POST /automation-runs/execute`
- 文件下载入口。

原因：

- 这些入口要么是历史工具，要么是轻量操作，要么存在业务口径未基础层化的问题。
- 不应抢在日报、P2、基础层入库前迁移。

建议：

- 历史工具保持同步。
- 资料归档可以未来迁移为 `DATA_IMPORT` 的扩展任务类型，但不是当前第一优先级。
- 下载入口继续兼容旧 `jobs`。

## 5. 风险分析

### 页面改造风险

- 现有页面是“点击后立即得到结果”的同步体验；任务化后可能变成“提交成功，稍后刷新状态”。
- 如果一次性改为异步轮询，页面需要新增状态页、错误提示、结果下载按钮和重试按钮，改动面较大。
- 建议先采用本地同步 TaskSubmitter，让页面响应与旧流程接近，再逐步引入任务状态页。

控制措施：

- 第一阶段迁移不改页面结构。
- 保留旧函数分支，支持快速回滚。
- 每个入口迁移前先建立 golden case：同一日期、同一基础层数据，新旧输出 CSV 必须一致。

### 数据一致性风险

- 当前正式 P1/P2 已要求从统一基础数据层读取；迁移时不能因为任务 payload 方便而直接传原始 CSV 数据生成正式结果。
- 如果任务提交和任务执行分离，可能出现提交时基础层有数据、执行时数据被新批次覆盖的问题。
- 现有 SQLite schema 没有通用 task 表和 result asset 表，状态与结果只能临时复用 automation task/run 和 jobs。

控制措施：

- `REPORT_GENERATE` 和 `AI_CONTENT_GENERATE` payload 只传 `brand_id/platform/channel/date/task_type`，不要传原始行作为正式计算来源。
- 任务执行时仍由 Service 通过 Repository 读取基础层。
- 后续 PostgreSQL 迁移时增加批次快照、任务输入快照和结果资产表。

### 用户体验风险

- 任务化后，如果没有状态页，用户无法知道任务是排队、运行、成功还是失败。
- AI 内容生成可能因为 API 配额、模型权限、网络超时失败，旧页面只显示一次错误；任务系统需要能保留失败原因。
- 数据缺失时，用户需要知道缺哪类基础层数据，而不是只看到“生成失败”。

控制措施：

- 先接 `TaskQueryService` 到只读管理页，再改高频入口。
- TaskResult 的 error 必须保留可读原因。
- 对日报和 P2 增加缺失数据清单：缺 product_order、store_finance、store_traffic、service_review 中哪一类。

## 建议落地顺序

1. 写只读任务状态管理页，先展示当前 `TaskQueryService` 的结果，不改变任何执行逻辑。
2. 给安踏美团日报加内部开关：默认旧流程，可切到 TaskSubmitter 本地同步流程。
3. 对 7 天日报做新旧输出一致性测试。
4. 迁移 P2 内容中心到 TaskSubmitter 本地同步流程。
5. 迁移插件导入到 DATA_IMPORT。
6. 等本地同步任务稳定后，再评估 Redis/Celery。

## 明确不在本阶段做的事

- 不修改 `app.py`。
- 不修改任何路由。
- 不修改 Service、Repository、processors。
- 不修改数据库 schema。
- 不接 Redis。
- 不接 Celery。
- 不改变现有页面运行方式。
