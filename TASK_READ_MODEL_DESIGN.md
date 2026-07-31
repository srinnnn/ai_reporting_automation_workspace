# TASK_READ_MODEL_DESIGN

生成日期：2026-07-31

当前阶段：Step 6-R - Task Read Model Design

执行边界：本阶段只生成设计文档，不修改 schema、Repository、TaskRunner 或任何业务代码。

## 1. 当前任务模型分析

### 1.1 automation_tasks

当前任务主数据来自 SQLite 表 `automation_tasks`，对应 `AutomationTaskRecord`。

现有字段：

```text
id
task_name
business_unit
brand_id
brand_name
platform
channel
file_type
frequency
scheduled_time
date_window
enabled
output_folder
owner
notes
created_at
updated_at
```

当前优点：

- 已经有 `brand_id`、`business_unit`、`platform`、`channel`、`owner`，具备 RBAC 需要的基础资源字段。
- 已经有 `enabled`，可以兼容 `cancelled` 或停用状态。
- 已经有 `output_folder`，可以用于 legacy 自动化交付路径。

当前不足：

- `file_type` 目前被 TaskQueryService 当成 `task_type` 使用，语义不够明确。
- 没有 `created_by`，只有 `owner`，无法区分“任务归属人”和“本次提交人”。
- 没有 `scope_snapshot`，无法审计任务创建时匹配了哪些品牌、部门、平台或渠道权限。
- 没有任务级 `status`，当前状态需要依赖最新 run 推导。

### 1.2 automation_runs

当前执行记录来自 SQLite 表 `automation_runs`，对应 `AutomationRunRecord`。

现有字段：

```text
id
task_id
task_name
run_date
status
downloaded_file_count
synced_file_count
message
executed_by
created_at
```

当前优点：

- 已经有 `task_id` 关联任务。
- 已经有 `status` 和 `executed_by`，可以表达一次执行的状态和执行人。
- 已经被 TaskService 复用为任务状态记录，低风险支撑了 Step 6-A 到 Step 6-Q。

当前不足：

- `message` 同时承载错误信息、普通消息和 JSON 结果摘要，职责混杂。
- 没有 `started_at`、`finished_at`、`updated_at`，不利于异步任务进度和耗时统计。
- 没有 `attempt`、`worker_id`、`queue_name`，不利于 Celery 重试和排障。
- 当前 TaskQueryService 只取最近 run 推导任务状态，历史执行链路无法完整展示。

### 1.3 TaskQueryService

当前 `TaskQueryService` 读取 `TaskRepository`：

```text
automation_tasks
automation_runs latest by task_id
        ↓
TaskReadModel
```

当前 `TaskReadModel` 字段：

```text
task_id
task_type
status
created_by
created_time
result
error
```

当前实现中：

- `task_id = automation_tasks.id`
- `task_type = automation_tasks.file_type`
- `created_by = automation_tasks.owner`
- `created_time = automation_tasks.created_at`
- `status = latest_run.status`，没有 run 时根据 `enabled` 推导为 `pending/cancelled`
- `result = json.loads(latest_run.message)`，解析失败则作为普通 message
- `error = latest_run.message`，仅当 latest run 为 `failed`

主要缺口：

- `brand_id`、`business_unit`、`platform`、`channel` 没有进入 read model，导致 PermissionService 只能对本人任务和 Admin 做强判断。
- `owner` 和 `created_by` 混在一起。
- `result_asset` 被嵌在 `result` 里，查询层、结果层、权限层都需要重复知道这个约定。
- 没有 `updated_at`，任务列表无法准确排序和显示最近变化。

### 1.4 TaskResultService

当前 `TaskResultService` 通过 `TaskQueryService.get_task(task_id)` 获取 read model，再从 `task.result.result_asset` 读取结果资产。

当前安全能力：

- 只允许成功任务下载。
- 校验 `result_asset.filename`。
- 校验文件路径在允许的 `result_dir` 内。
- 前端只返回 `task-results/<task_id>/<filename>` 这种安全路径，不暴露真实服务器路径。

当前不足：

- 结果资产与 run message 耦合。
- 没有独立结果表，无法保存多个输出文件、版本、MIME 类型、校验和、过期时间。
- 没有下载权限快照和审计记录。

## 2. 正式 Task Read Model 设计

正式 read model 建议定义为稳定的后端只读 DTO，供页面、API、PermissionService、TaskResultService、未来 Celery 监控页共用。

建议字段：

```text
task_id
task_type
status
created_by
owner
brand_id
business_unit
platform
channel
scope_snapshot
result_asset
created_at
updated_at
```

### 2.1 字段定义

| 字段 | 类型 | 必填 | 含义 | 来源 |
|---|---|---:|---|---|
| task_id | int | 是 | 系统内部任务 ID | tasks.id |
| task_type | str | 是 | 任务类型，如 DATA_IMPORT、REPORT_GENERATE、AI_CONTENT_GENERATE | tasks.task_type |
| status | str | 是 | 当前任务状态 | tasks.status 或 latest task_runs.status |
| created_by | str | 是 | 提交任务的用户 | tasks.created_by |
| owner | str | 是 | 任务归属人或负责人 | tasks.owner |
| brand_id | str | 是 | 品牌 ID，如 anta_kids | tasks.brand_id |
| business_unit | str | 是 | 业务组/部门，如 anta_retail_team | tasks.business_unit |
| platform | str | 是 | 平台，如 meituan、jd、tmall | tasks.platform |
| channel | str | 是 | 渠道，如 instant_retail | tasks.channel |
| scope_snapshot | dict | 是 | 创建任务时的权限范围快照 | tasks.scope_snapshot_json |
| result_asset | dict/null | 否 | 任务成功后的可下载资产摘要 | task_results 或 latest run result |
| created_at | str/datetime | 是 | 任务创建时间 | tasks.created_at |
| updated_at | str/datetime | 是 | 任务最后更新时间 | tasks.updated_at |

### 2.2 scope_snapshot 建议结构

```json
{
  "created_by": "alice",
  "submitted_role": "operator",
  "brand_scope": ["anta_kids"],
  "department_scope": ["anta_retail_team"],
  "platform_scope": ["meituan"],
  "channel_scope": ["instant_retail"],
  "matched_rule": "created_by_or_brand_scope",
  "policy_version": "task-permission-v1"
}
```

用途：

- 审计任务创建时为什么允许提交。
- 排查后续权限变更导致的可见范围变化。
- 为多品牌、多平台隔离提供明确上下文。

### 2.3 result_asset 建议结构

```json
{
  "asset_id": 1001,
  "filename": "anta_meituan_daily_20260725.csv",
  "mime_type": "text/csv",
  "size": 20480,
  "checksum": "sha256:...",
  "public_path": "task-results/123/anta_meituan_daily_20260725.csv",
  "created_at": "2026-07-31T11:00:00+08:00"
}
```

要求：

- `public_path` 只用于前端展示，不是真实服务器绝对路径。
- 真实路径只允许在 `TaskResultService.get_download_info()` 内部使用。
- `checksum` 用于后续校验重复生成和文件损坏。

## 3. 状态模型设计

正式状态枚举：

```text
pending
running
success
failed
cancelled
```

状态含义：

| 状态 | 含义 | 可下载 | 可重试 |
|---|---|---:|---:|
| pending | 已创建，尚未执行 | 否 | 是 |
| running | 正在执行 | 否 | 否 |
| success | 执行成功 | 取决于 result_asset | 是 |
| failed | 执行失败 | 否 | 是 |
| cancelled | 已取消或被停用 | 否 | 是 |

推荐状态流：

```text
pending -> running -> success
pending -> running -> failed
pending -> cancelled
running -> failed
failed -> pending   # retry creates a new run or new attempt
success -> pending  # manual rerun
```

状态更新原则：

- `tasks.status` 保存当前最终状态，便于列表快速查询。
- `task_runs.status` 保存每次执行状态，便于审计和重试。
- Worker 只能通过 TaskService 或 Repository 更新状态，不能直接改数据库。
- 状态更新必须幂等，重复收到同一 task result 不应生成脏数据。

## 4. 与 RBAC 的关系

`PermissionService` 应使用正式 read model 做权限判断，而不是直接读取数据库。

### 4.1 can_view_task

判断逻辑：

```text
Admin
OR task.created_by == current_user.username
OR task.owner == current_user.username
OR user.brand_scope contains task.brand_id
OR user.department_scope contains task.business_unit
OR user.platform_scope/channel_scope matches task.platform/task.channel
```

核心依赖字段：

```text
created_by
owner
brand_id
business_unit
platform
channel
scope_snapshot
```

### 4.2 can_download_task

判断逻辑：

```text
can_view_task(user, task)
AND task.status == "success"
AND task.result_asset is not null
AND user has task.download
AND TaskResultService validates file safety
```

### 4.3 can_submit_task

提交时使用 payload 与用户 scope 做预检查：

```text
payload.brand_id in user.brand_scope
payload.business_unit in user.department_scope
payload.platform in user.platform_scope
payload.channel in user.channel_scope
```

提交成功后写入：

```text
created_by = session_user.username
owner = payload.owner or session_user.username
scope_snapshot = matched permission context
```

注意：

- 客户端传入的 `created_by` 不能作为可信来源。
- API 层应以 session/API token 识别的用户为准。
- Viewer 默认禁止提交，即使 payload 在其查看范围内。

## 5. PostgreSQL 迁移设计

建议未来拆成三张核心表：

```text
tasks
task_runs
task_results
```

### 5.1 tasks

用途：任务主表，保存当前任务状态和权限资源字段。

建议字段：

```text
id BIGSERIAL PRIMARY KEY
task_type TEXT NOT NULL
task_name TEXT NOT NULL
status TEXT NOT NULL
created_by TEXT NOT NULL
owner TEXT NOT NULL
brand_id TEXT NOT NULL
business_unit TEXT NOT NULL
platform TEXT NOT NULL
channel TEXT NOT NULL
payload_json JSONB NOT NULL
scope_snapshot_json JSONB NOT NULL
idempotency_key TEXT NOT NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
cancelled_at TIMESTAMPTZ NULL
```

建议索引：

```text
idx_tasks_status_updated_at(status, updated_at DESC)
idx_tasks_created_by(created_by, updated_at DESC)
idx_tasks_scope(brand_id, business_unit, platform, channel)
uniq_tasks_idempotency_key(idempotency_key)
```

从现有字段映射：

| 现有来源 | 新字段 |
|---|---|
| automation_tasks.id | tasks.id |
| automation_tasks.file_type | tasks.task_type |
| automation_tasks.task_name | tasks.task_name |
| latest automation_runs.status 或 enabled 推导 | tasks.status |
| automation_tasks.owner | tasks.owner |
| automation_tasks.owner | tasks.created_by，迁移期兼容 |
| automation_tasks.brand_id | tasks.brand_id |
| automation_tasks.business_unit | tasks.business_unit |
| automation_tasks.platform | tasks.platform |
| automation_tasks.channel | tasks.channel |
| automation_tasks.created_at | tasks.created_at |
| automation_tasks.updated_at | tasks.updated_at |

### 5.2 task_runs

用途：任务执行历史表，保存每次执行和重试。

建议字段：

```text
id BIGSERIAL PRIMARY KEY
task_id BIGINT NOT NULL REFERENCES tasks(id)
attempt INTEGER NOT NULL
status TEXT NOT NULL
queue_name TEXT NOT NULL
worker_id TEXT NULL
started_at TIMESTAMPTZ NULL
finished_at TIMESTAMPTZ NULL
error_code TEXT NOT NULL DEFAULT ''
error_message TEXT NOT NULL DEFAULT ''
progress_json JSONB NOT NULL DEFAULT '{}'
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

建议索引：

```text
idx_task_runs_task_id_attempt(task_id, attempt DESC)
idx_task_runs_status_created_at(status, created_at DESC)
```

从现有字段映射：

| 现有来源 | 新字段 |
|---|---|
| automation_runs.id | task_runs.id |
| automation_runs.task_id | task_runs.task_id |
| automation_runs.status | task_runs.status |
| automation_runs.executed_by | task_runs.worker_id 或 progress_json.executed_by |
| automation_runs.message | task_runs.error_message 或 progress_json.legacy_message |
| automation_runs.created_at | task_runs.created_at |

### 5.3 task_results

用途：任务结果资产表，保存可下载文件和结果摘要。

建议字段：

```text
id BIGSERIAL PRIMARY KEY
task_id BIGINT NOT NULL REFERENCES tasks(id)
run_id BIGINT NULL REFERENCES task_runs(id)
asset_type TEXT NOT NULL
filename TEXT NOT NULL
storage_path TEXT NOT NULL
public_path TEXT NOT NULL
mime_type TEXT NOT NULL
size_bytes BIGINT NOT NULL
checksum TEXT NOT NULL
summary_json JSONB NOT NULL DEFAULT '{}'
created_at TIMESTAMPTZ NOT NULL
expires_at TIMESTAMPTZ NULL
```

建议索引：

```text
idx_task_results_task_id_created_at(task_id, created_at DESC)
idx_task_results_public_path(public_path)
```

从现有字段映射：

| 现有来源 | 新字段 |
|---|---|
| latest_run.message.result_asset.filename | task_results.filename |
| latest_run.message.result_asset.file_path/path | task_results.storage_path |
| TaskResultService public path | task_results.public_path |
| latest_run.message.result_asset.size | task_results.size_bytes |
| latest_run.message.summary 或 output_row_count | task_results.summary_json |

## 6. Celery 兼容设计

未来 Celery Worker 应只依赖任务协议和服务层，不直接依赖 Flask 页面或 raw file 路径扫描。

### 6.1 提交流程

```text
Controller/API
  -> PermissionService.can_submit_task()
  -> TaskSubmitter.submit()
  -> TaskService.create_task()
  -> enqueue Celery task with task_id
```

队列消息只传最小信息：

```json
{
  "task_id": 123,
  "task_type": "REPORT_GENERATE"
}
```

不建议把完整 payload 和敏感路径放进 Celery message，原因：

- Broker 消息可能被日志或监控系统采集。
- payload 过大会影响队列性能。
- 正式任务数据应以数据库为准。

### 6.2 执行流程

```text
Celery Worker
  -> TaskRepository.get_task(task_id)
  -> TaskService.update_task_status(running)
  -> TaskRunner.run(TaskRequest)
  -> Executor
  -> Service
  -> ResultAssetService
  -> TaskService.update_task_status(success/failed)
  -> TaskResultRepository.save_result()
```

### 6.3 幂等与重试

必须支持：

- `idempotency_key` 防止重复提交同一任务。
- `attempt` 记录第几次执行。
- 结果文件命名包含 task_id/run_id 或 checksum，避免覆盖。
- Worker 崩溃后可根据 `running` 超时任务重新入队。

### 6.4 并发控制

建议：

- 同一 `brand_id/platform/channel/date` 的日报任务加业务锁，避免多人重复生成。
- 文件保存用临时文件写入，完成后原子 rename。
- Task 状态更新使用事务，避免 `success` 结果和 `failed` 状态不一致。

### 6.5 监控字段

正式 read model 应支持未来页面展示：

```text
queue_name
worker_id
attempt
started_at
finished_at
duration_seconds
error_code
error_message
```

这些字段可以来自 `task_runs`，不一定全部进入第一版 TaskReadModel，但设计上需要兼容。

## 7. 渐进式实施建议

本阶段不改代码。后续建议按以下顺序迁移：

1. 扩展 `TaskReadModel` dataclass，先把 `brand_id/business_unit/platform/channel/owner/updated_at/result_asset` 从现有 `AutomationTaskRecord` 和 run JSON 带出来。
2. 更新 `TaskQueryService._build_read_model()`，不改 SQLite schema，只扩展 read model 输出。
3. 更新 `PermissionService`，从 read model 读取正式字段，不再依赖 role 字符串里的临时 scope 表达。
4. 增加 API 和页面测试，覆盖业务负责人按品牌/部门可见。
5. 设计 PostgreSQL migration，但继续保留 SQLite 开发模式。
6. 增加正式 `tasks/task_runs/task_results` 表后，再把 Repository Adapter 切到新表。
7. 最后引入 Redis/Celery，让 Worker 只通过 task_id 读取任务。

## 8. 验收标准

正式 Task Read Model 迁移完成后应满足：

- `/tasks` 可以按用户权限过滤品牌、部门、平台、渠道任务。
- `/api/tasks/<task_id>` 不暴露未授权任务。
- `/api/tasks/<task_id>/download` 只允许成功且有结果资产的授权任务下载。
- TaskResultService 不再需要解析 run message 里的 result_asset。
- PermissionService 不直接访问数据库。
- SQLite 开发模式仍可运行。
- PostgreSQL 表结构可以承载 20+ 用户并发、历史任务、重试和结果资产。
- Celery Worker 可以只凭 `task_id` 获取完整执行上下文。

## 9. 当前阶段结论

当前任务体系已经具备低风险任务化基础，但 read model 仍偏临时：

- 权限字段存在于 `automation_tasks`，但没有完整暴露到 `TaskReadModel`。
- 结果资产存在于 run message JSON，尚未独立建模。
- 状态来自最新 run 推导，不适合长期并发任务监控。

下一步最合适的低风险动作是：不改 schema，仅扩展 `TaskReadModel` 字段，并让 `TaskQueryService` 从现有 `AutomationTaskRecord` 补齐 `brand_id/business_unit/platform/channel/owner/updated_at/result_asset`。这样可以让 Step 6-Q 的 PermissionService 真正按品牌和部门生效，同时继续保持 SQLite 与 legacy 流程稳定。
