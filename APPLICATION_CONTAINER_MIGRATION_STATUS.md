# APPLICATION_CONTAINER_MIGRATION_STATUS

生成日期：2026-08-03

当前阶段：Step 7-E-M - ApplicationContainer Migration Status

执行边界：本文件只盘点 ApplicationContainer 迁移状态，不修改代码、不连接数据库、不执行 SQL、不引入 Redis/Celery。

## 1. 当前 ApplicationContainer 结构

当前容器入口位于：

```text
backend/core/container.py
```

当前结构：

```text
ApplicationContainer
  config: CoreConfig
  logger: logging.Logger
  repositories: RepositoryBundle
  services: ServiceBundle
  workers: WorkerBundle
```

### RepositoryBundle

```text
users: UserRepository
foundation: FoundationRepository
reports: ReportRepository
tasks: TaskRepository
```

当前实现只装配 SQLite Adapter，且通过 legacy `AppStorage` 适配现有 SQLite 行为。

### ServiceBundle

```text
data_foundation: DataFoundationService
reports: ReportService
ai: AIService
ai_content: AIContentService
result_assets: ResultAssetService
tasks: TaskService
task_query: TaskQueryService
task_result: TaskResultService
permissions: PermissionService
task_submitter: TaskSubmitter | None
```

说明：

- `task_submitter` 是为了 route 解析方便暴露在 `services` 上。
- 实际实例与 `workers.task_submitter` 为同一个同步 TaskSubmitter。
- 这不是万能 Factory；业务代码不应持有 container 或调用 container 创建依赖。

### WorkerBundle

```text
data_import_executor: DataImportExecutor
report_executor: ReportExecutor
ai_content_executor: AIContentExecutor
task_runner: TaskRunner
task_submitter: TaskSubmitter
```

当前 Worker 仍为本地同步执行，不接 Redis、不接 Celery。

## 2. 已迁移组件

已迁移的含义：route/service resolver 优先从 `app.container.services` 或 `app.container.workers` 获取实例，并保留 legacy fallback。

| 模块 | 当前依赖来源 | 是否进入 Container | 迁移风险 | 建议迁移顺序 |
| --- | --- | --- | --- | --- |
| TaskQueryService | `app.container.services.task_query`，fallback 为 `SQLiteTaskRepository(self.storage)` | 是，且 route resolver 已优先使用 | 低。只读查询，主要风险是 SQLite schema 未初始化 | 已完成 |
| TaskResultService | `app.container.services.task_result`，fallback 为 `TaskResultService(self._task_query_service(), self.config.result_dir)` | 是，且 route resolver 已优先使用 | 低。依赖任务结果 asset 路径安全校验 | 已完成 |
| PermissionService | `app.container.services.permissions`，fallback 为 `PermissionService()` | 是，且 route resolver 已优先使用 | 低。当前仍是 MVP 权限，不涉及 schema | 已完成 |
| TaskSubmitter | `app.container.services.task_submitter`，fallback 为 legacy 本地 `TaskSubmitter(TaskService, TaskRunner)` | 是，且 `_task_submitter()` 已优先使用 | 中。虽然仍同步执行，但会触发任务创建、执行和结果保存 | 已完成，继续观察 |
| TaskRunner | `app.container.workers.task_runner`，由 `TaskSubmitter` 间接使用 | 是，未直接暴露给 route | 中。涉及 executor 分发，但当前未改变状态流转 | 已装配，暂不直接迁移 route |
| Executors | `app.container.workers.*_executor`，由 `TaskRunner` 使用 | 是，未直接暴露给 route | 中。执行器会调用 Report/Foundation/AI 服务，但本阶段没有改业务逻辑 | 已装配，暂不直接迁移 route |

## 3. 未迁移组件

未迁移的含义：虽然部分对象已被 Container 装配，但 legacy route 仍未改为正式依赖 container；业务流程仍按原路径执行。

| 模块 | 当前依赖来源 | 是否进入 Container | 迁移风险 | 建议迁移顺序 |
| --- | --- | --- | --- | --- |
| ReportService | Container 已装配 `services.reports`；legacy report routes 仍使用 app.py 原有流程或 task fallback 内本地构造 | 部分进入，route 未正式迁移 | 高。涉及日报/周报输出口径、基础层读取、下载交付物 | 暂缓。先做结果一致性对比和灰度开关 |
| ReportExecutor | Container 已装配 `workers.report_executor`；TaskRunner 通过 container submitter 间接使用 | 是，但业务 route 未直接迁移 | 中到高。Executor 调用 ReportService，并保存 ResultAsset | 暂缓直接迁移 route；继续通过 TaskSubmitter 间接验证 |
| AIService | Container 已装配 `services.ai`；P2 legacy route 仍可能直接创建 AI client 或调用现有 pipeline | 部分进入，route 未正式迁移 | 高。涉及 API Key、模型错误、Prompt 输出字段和成本追踪 | 暂缓。先设计 AI run 记录和 mock 测试 |
| AIContentService | Container 已装配 `services.ai_content`；P2 route 未正式迁移 | 部分进入，route 未正式迁移 | 高。涉及选品、文案、Prompt 结构和业务输出字段 | 暂缓。必须先做 P2 输出一致性测试 |
| FoundationService | Container 已装配 `services.data_foundation`；legacy 上传/入库 route 仍使用 app.py 原始流程 | 部分进入，route 未正式迁移 | 高。涉及字段映射、品牌判定、清洗和入库 | 暂缓。先做 intake-to-foundation E2E 测试 |
| Legacy AppStorage 调用 | `intranet_app/app.py` 和 legacy 页面仍直接使用 `self.storage` | 否。仅通过 SQLite Repository Adapter 被间接适配 | 高。承担用户、session、job、task、foundation、report 等历史职责 | 暂缓删除；保持 Legacy Adapter 冻结边界 |

## 4. 迁移边界说明

### 当前允许

- route resolver 优先读取 `app.container.services`。
- 没有 container 时继续走 legacy fallback。
- Container 内部可以装配 SQLite Repository Adapter。
- TaskSubmitter 继续同步执行，状态流转不变。
- 只读任务页面和任务 API 查询使用 container 解析服务。

### 当前禁止

当前阶段不修改：

- processor
- database schema
- PostgreSQL
- Redis
- Celery

同时禁止：

- 删除 `storage.py` 或直接重构 `AppStorage`。
- 删除 legacy route/service 创建代码。
- 修改日报、周报、月报计算口径。
- 修改 AI Prompt、AI 输出字段或默认模型配置。
- 修改基础数据层字段名、清洗规则或金额计算逻辑。
- 将 `ApplicationContainer` 传入业务 Service 构造函数。
- 新增 `container.get_everything()` 或万能 Factory。

## 5. 建议后续迁移顺序

| 顺序 | 模块 | 建议动作 | 前置条件 |
| --- | --- | --- | --- |
| 1 | Task pages/API read path | 继续观察现有 container 解析稳定性 | 现有 203+ 测试持续通过 |
| 2 | TaskSubmitter path | 保持同步，增加更多 API 提交 fixture | 已完成基础迁移，需补失败场景测试 |
| 3 | ResultAsset read/write path | 把 asset provider 配置化，但仍使用 LocalStorageProvider | 不改下载 URL、不改文件路径安全策略 |
| 4 | ReportService Task path | 只在 Task 模式下做新旧结果一致性对比 | 同一天数据行数、金额、核心字段一致 |
| 5 | FoundationService | 先做 intake-to-foundation E2E，再迁移 route | 字段映射和品牌判定测试完整 |
| 6 | AIService/AIContentService | 先做 mock AI 和 AI run 记录，再迁移 route | 不真实调用外部 API，不改 Prompt |
| 7 | AppStorage legacy shrink | 只在 PostgreSQL Adapter 成熟后逐步缩小职责 | schema 迁移方案、回滚方案、数据校验齐备 |

## 6. 当前结论

ApplicationContainer 已经具备进程级依赖装配能力，并已接入低风险任务相关 resolver。

当前状态适合继续做小步迁移，但不适合迁移 Report、AI、Foundation 主业务流程。下一步应优先补足任务提交失败场景、结果资产一致性和 E2E 测试，再决定是否将某一个业务 route 切到 container 服务。