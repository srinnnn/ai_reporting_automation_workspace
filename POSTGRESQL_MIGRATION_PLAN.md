# POSTGRESQL_MIGRATION_PLAN

生成日期：2026-07-31

当前阶段：Step 7-A - PostgreSQL Migration Plan

执行边界：本阶段只生成设计文档，不修改代码、不修改数据库 schema、不修改 Task 流程。

## 1. 当前 SQLite 架构分析

### 1.1 storage.py 当前职责

当前系统的本地数据库入口集中在 `intranet_app/storage.py` 的 `AppStorage`。

`AppStorage` 当前承担：

- 用户与 session 存储。
- legacy job/report 存储。
- 自动化任务配置和执行记录存储。
- 数据基础层导入批次、源文件、字段映射、校验报告、缺失数据项存储。
- 美团事实表和维表存储。
- 项目反馈、提效映射等管理数据存储。

风险判断：

- `storage.py` 职责偏重，既是 schema 管理，又是 DAO，又包含一部分业务默认数据初始化。
- 当前 SQLite 适合单机开发和本地试点，不适合 20+ 用户并发上传、任务执行、报表查询和 AI 任务状态更新。
- SQLite 写锁会成为上传、任务状态更新、报表保存并发时的瓶颈。
- 生产环境需要把连接管理、事务、索引、备份、权限、迁移版本管理交给 PostgreSQL。

### 1.2 automation_tasks

当前 `automation_tasks` 表字段：

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

当前用途：

- 保存自动化任务配置。
- 被 `SQLiteTaskRepository.create_task()` 和任务状态页面读取。
- 当前 `TaskReadModel` 已经从它补齐 `brand_id/business_unit/platform/channel/owner/updated_at/scope_snapshot`。

主要缺口：

- `file_type` 与正式 `task_type` 语义混用。
- 没有 `status` 字段，任务状态依赖最新一条 `automation_runs` 推导。
- 没有 `created_by`，目前迁移期只能用 `owner` 兼容。
- 没有 `payload_json` 和 `scope_snapshot_json` 原始字段。
- 没有 `idempotency_key`，无法防重复提交。

### 1.3 automation_runs

当前 `automation_runs` 表字段：

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

当前用途：

- 保存一次自动化任务执行记录。
- `TaskQueryService` 取最近一条 run 推导任务状态。
- `TaskResultService` 通过 run message JSON 获取 legacy `result_asset`。

主要缺口：

- `message` 同时承载错误、普通消息、JSON 结果摘要和 result asset。
- 没有 `attempt`、`worker_id`、`queue_name`。
- 没有 `started_at/finished_at/updated_at`。
- 没有结构化错误字段 `error_code/error_message`。
- 无法高效查询任务执行历史和重试链路。

### 1.4 现有 Repository

当前抽象接口在 `backend/repositories/interfaces.py`：

```text
UserRepository
FoundationRepository
ReportRepository
TaskRepository
```

当前 SQLite Adapter：

```text
backend/repositories/sqlite/user_repository.py
backend/repositories/sqlite/foundation_repository.py
backend/repositories/sqlite/report_repository.py
backend/repositories/sqlite/task_repository.py
```

当前迁移优势：

- Service 层已经开始依赖 Repository 抽象。
- 后续可以新增 PostgreSQL Adapter，并通过配置切换。
- 不需要让 Controller 或 Service 直接知道 SQLite/PostgreSQL 差异。

当前限制：

- 部分 legacy `app.py` 仍直接调用 `AppStorage`。
- TaskRepository 当前返回的仍是 `AutomationTaskRecord/AutomationRunRecord`，未来需要逐步引入正式 Task DTO。
- SQLite Adapter 仍是对 `AppStorage` 的兼容包装，不是独立数据访问实现。

## 2. PostgreSQL 目标架构

生产库建议以 PostgreSQL 作为主数据库，Redis 只作为异步队列和缓存，不作为业务事实存储。

核心表：

```text
users
tasks
task_runs
task_results
reports
assets
```

### 2.1 users

用途：用户主表。

建议字段：

```sql
id BIGSERIAL PRIMARY KEY,
username TEXT NOT NULL UNIQUE,
display_name TEXT NOT NULL,
email TEXT NOT NULL DEFAULT '',
role TEXT NOT NULL,
password_salt TEXT NOT NULL,
password_digest TEXT NOT NULL,
status TEXT NOT NULL DEFAULT 'active',
last_login_at TIMESTAMPTZ NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL
```

迁移说明：

- 先保留 `role` 文本字段，兼容当前 `UserRecord.role`。
- 正式 RBAC 表可后续新增，不阻塞 PostgreSQL 初迁移。
- 密码摘要原样迁移，不重新生成。

建议索引：

```sql
CREATE UNIQUE INDEX ux_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);
```

### 2.2 tasks

用途：正式任务主表。

建议字段：

```sql
id BIGSERIAL PRIMARY KEY,
task_type TEXT NOT NULL,
task_name TEXT NOT NULL,
status TEXT NOT NULL,
created_by TEXT NOT NULL,
owner TEXT NOT NULL,
brand_id TEXT NOT NULL,
brand_name TEXT NOT NULL DEFAULT '',
business_unit TEXT NOT NULL,
platform TEXT NOT NULL,
channel TEXT NOT NULL,
payload_json JSONB NOT NULL DEFAULT '{}',
scope_snapshot_json JSONB NOT NULL DEFAULT '{}',
idempotency_key TEXT NOT NULL,
output_folder TEXT NOT NULL DEFAULT '',
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
cancelled_at TIMESTAMPTZ NULL
```

状态枚举：

```text
pending
running
success
failed
cancelled
```

建议索引：

```sql
CREATE UNIQUE INDEX ux_tasks_idempotency_key ON tasks(idempotency_key);
CREATE INDEX idx_tasks_status_updated_at ON tasks(status, updated_at DESC);
CREATE INDEX idx_tasks_created_by_updated_at ON tasks(created_by, updated_at DESC);
CREATE INDEX idx_tasks_scope ON tasks(brand_id, business_unit, platform, channel);
CREATE INDEX idx_tasks_type_scope ON tasks(task_type, brand_id, platform, channel);
```

从 SQLite 映射：

| SQLite 来源 | PostgreSQL 字段 |
|---|---|
| automation_tasks.id | tasks.id |
| automation_tasks.file_type | tasks.task_type |
| automation_tasks.task_name | tasks.task_name |
| latest automation_runs.status 或 enabled 推导 | tasks.status |
| automation_tasks.owner | tasks.created_by，迁移期兼容 |
| automation_tasks.owner | tasks.owner |
| automation_tasks.brand_id | tasks.brand_id |
| automation_tasks.brand_name | tasks.brand_name |
| automation_tasks.business_unit | tasks.business_unit |
| automation_tasks.platform | tasks.platform |
| automation_tasks.channel | tasks.channel |
| automation_tasks.output_folder | tasks.output_folder |
| automation_tasks.created_at | tasks.created_at |
| automation_tasks.updated_at | tasks.updated_at |

### 2.3 task_runs

用途：任务执行历史、重试、Worker 审计。

建议字段：

```sql
id BIGSERIAL PRIMARY KEY,
task_id BIGINT NOT NULL REFERENCES tasks(id),
attempt INTEGER NOT NULL,
status TEXT NOT NULL,
queue_name TEXT NOT NULL DEFAULT 'default',
worker_id TEXT NOT NULL DEFAULT '',
started_at TIMESTAMPTZ NULL,
finished_at TIMESTAMPTZ NULL,
error_code TEXT NOT NULL DEFAULT '',
error_message TEXT NOT NULL DEFAULT '',
progress_json JSONB NOT NULL DEFAULT '{}',
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL
```

建议索引：

```sql
CREATE INDEX idx_task_runs_task_attempt ON task_runs(task_id, attempt DESC);
CREATE INDEX idx_task_runs_status_created_at ON task_runs(status, created_at DESC);
CREATE INDEX idx_task_runs_worker ON task_runs(worker_id, created_at DESC);
```

从 SQLite 映射：

| SQLite 来源 | PostgreSQL 字段 |
|---|---|
| automation_runs.id | task_runs.id |
| automation_runs.task_id | task_runs.task_id |
| run order by task_id | task_runs.attempt |
| automation_runs.status | task_runs.status |
| automation_runs.executed_by | task_runs.worker_id 或 progress_json.executed_by |
| automation_runs.message | task_runs.error_message 或 progress_json.legacy_message |
| automation_runs.created_at | task_runs.created_at / updated_at |

### 2.4 task_results

用途：任务结果资产和摘要。

建议字段：

```sql
id BIGSERIAL PRIMARY KEY,
task_id BIGINT NOT NULL REFERENCES tasks(id),
run_id BIGINT NULL REFERENCES task_runs(id),
asset_id BIGINT NULL,
result_type TEXT NOT NULL,
filename TEXT NOT NULL,
storage_path TEXT NOT NULL,
public_path TEXT NOT NULL,
mime_type TEXT NOT NULL,
size_bytes BIGINT NOT NULL,
checksum TEXT NOT NULL DEFAULT '',
summary_json JSONB NOT NULL DEFAULT '{}',
created_at TIMESTAMPTZ NOT NULL,
expires_at TIMESTAMPTZ NULL
```

建议索引：

```sql
CREATE INDEX idx_task_results_task_created_at ON task_results(task_id, created_at DESC);
CREATE INDEX idx_task_results_run_id ON task_results(run_id);
CREATE INDEX idx_task_results_asset_id ON task_results(asset_id);
```

迁移说明：

- 当前 `automation_runs.message.result_asset` 迁移到 `task_results`。
- `summary_json` 保留 `output_row_count/summary` 等现有结果摘要。
- `storage_path` 是服务器内部路径，禁止直接返回前端。
- `public_path` 是安全展示路径，如 `task-results/123/daily.csv`。

### 2.5 reports

用途：正式报表交付记录，替代或兼容 legacy `jobs`。

建议字段：

```sql
id BIGSERIAL PRIMARY KEY,
module TEXT NOT NULL,
report_type TEXT NOT NULL,
title TEXT NOT NULL,
brand_id TEXT NOT NULL DEFAULT '',
brand_name TEXT NOT NULL DEFAULT '',
business_type TEXT NOT NULL,
platform TEXT NOT NULL DEFAULT '',
channel TEXT NOT NULL DEFAULT '',
task_id BIGINT NULL REFERENCES tasks(id),
asset_id BIGINT NULL,
created_by TEXT NOT NULL,
summary_json JSONB NOT NULL DEFAULT '{}',
warnings_json JSONB NOT NULL DEFAULT '[]',
created_at TIMESTAMPTZ NOT NULL
```

建议索引：

```sql
CREATE INDEX idx_reports_brand_created_at ON reports(brand_id, created_at DESC);
CREATE INDEX idx_reports_task_id ON reports(task_id);
CREATE INDEX idx_reports_created_by ON reports(created_by, created_at DESC);
```

迁移说明：

- legacy `jobs` 可迁移为 `reports` + `assets`。
- P1 日报、周报、月报输出都应形成 `reports` 记录。

### 2.6 assets

用途：统一文件资产表，包括报表 CSV、AI 内容交付包、上传模板、生成图片等。

建议字段：

```sql
id BIGSERIAL PRIMARY KEY,
asset_type TEXT NOT NULL,
filename TEXT NOT NULL,
storage_path TEXT NOT NULL,
public_path TEXT NOT NULL,
mime_type TEXT NOT NULL,
size_bytes BIGINT NOT NULL,
checksum TEXT NOT NULL,
created_by TEXT NOT NULL,
brand_id TEXT NOT NULL DEFAULT '',
business_unit TEXT NOT NULL DEFAULT '',
platform TEXT NOT NULL DEFAULT '',
channel TEXT NOT NULL DEFAULT '',
metadata_json JSONB NOT NULL DEFAULT '{}',
created_at TIMESTAMPTZ NOT NULL,
expires_at TIMESTAMPTZ NULL
```

建议索引：

```sql
CREATE INDEX idx_assets_type_created_at ON assets(asset_type, created_at DESC);
CREATE INDEX idx_assets_scope ON assets(brand_id, business_unit, platform, channel);
CREATE INDEX idx_assets_checksum ON assets(checksum);
```

注意：

- 数据库只存文件元数据，不存大文件二进制。
- 文件本体先放服务器挂载卷，后续可迁移到 OSS/S3。
- `storage_path` 不返回前端，下载必须经过服务层校验。

## 3. Repository 迁移方案

目标：保持 Service 层接口不变，通过 Adapter 替换数据库实现。

当前：

```text
Service
  -> Repository Interface
  -> SQLite Adapter
  -> AppStorage
  -> SQLite
```

目标：

```text
Service
  -> Repository Interface
  -> PostgreSQL Adapter
  -> PostgreSQL
```

### 3.1 保持接口不变

第一阶段不改：

```text
UserRepository
FoundationRepository
ReportRepository
TaskRepository
```

新增目录建议：

```text
backend/repositories/postgresql/
  __init__.py
  user_repository.py
  foundation_repository.py
  report_repository.py
  task_repository.py
```

### 3.2 配置切换

新增配置项建议：

```text
DB_BACKEND=sqlite|postgresql
DATABASE_URL=postgresql://...
```

Repository 工厂建议：

```text
backend/repositories/factory.py
```

职责：

- 根据 `DB_BACKEND` 创建 SQLite 或 PostgreSQL Adapter。
- Service 不直接 import 具体 Adapter。
- 开发环境默认 SQLite。
- 生产环境必须 PostgreSQL。

### 3.3 PostgreSQL Adapter 规则

要求：

- 每个 Repository 方法使用明确事务边界。
- 所有 SQL 参数化，禁止字符串拼接。
- 金额类字段保持 Decimal 或文本标准化，不使用 float。
- JSON 字段使用 JSONB，进入数据库前做结构校验。
- 查询任务列表必须支持分页和过滤，不能全表扫描后 Python 过滤。

### 3.4 接口演进顺序

先保持兼容：

```text
TaskRepository.get_task() -> AutomationTaskRecord
TaskRepository.list_task_runs() -> list[AutomationRunRecord]
```

再新增正式接口：

```text
TaskRepository.get_task_read_model(task_id)
TaskRepository.list_task_read_models(filters)
TaskResultRepository.get_latest_result(task_id)
```

最后替换 `TaskQueryService` 的数据来源。

## 4. 数据迁移方案

数据迁移分四步：

```text
导出
转换
导入
校验
```

### 4.1 导出

从 SQLite 导出：

```text
users
sessions，可选，不建议迁移到生产
jobs
automation_tasks
automation_runs
import_batches
source_files
validation_reports
missing_data_items
fact_order_product
fact_store_finance
fact_store_traffic
fact_service_review
dim_product
dim_store
target_plan
dim_campaign
dim_platform_shop
dim_channel_product
```

导出格式：

```text
CSV for flat tables
JSONL for rows with JSON-like message fields
manifest.json for export metadata
```

导出 manifest 建议：

```json
{
  "export_time": "2026-07-31T12:00:00+08:00",
  "source_db": "runtime/app.db",
  "tables": {
    "automation_tasks": {"row_count": 10, "checksum": "sha256:..."}
  }
}
```

### 4.2 转换

转换规则：

- `automation_tasks` -> `tasks`
- `automation_runs` -> `task_runs`
- `automation_runs.message.result_asset` -> `task_results`
- `jobs` -> `reports` + `assets`
- `users` -> `users`

关键转换：

```text
tasks.task_type = automation_tasks.file_type
tasks.created_by = automation_tasks.owner
tasks.owner = automation_tasks.owner
tasks.status = latest valid automation_runs.status or enabled-derived status
tasks.scope_snapshot_json = brand/business/platform/channel/owner snapshot
tasks.idempotency_key = sha256(task_type + brand_id + platform + channel + date_window + owner + created_at)
```

run message 解析：

```text
if status == failed:
  error_message = message after "error:" if present
else if message is JSON object:
  progress_json = parsed message without result_asset
  result_asset -> task_results
else:
  progress_json.legacy_message = message
```

### 4.3 导入

导入顺序：

```text
users
assets
tasks
task_runs
task_results
reports
foundation/source tables
fact/dim tables
```

导入要求：

- 单表批量导入使用事务。
- 外键相关表按依赖顺序导入。
- 导入前先建临时 staging 表。
- staging 校验通过后再写正式表。
- 导入过程保留 `legacy_id` 映射表，便于回查。

建议临时表：

```text
migration_legacy_id_map(
  source_table,
  source_id,
  target_table,
  target_id
)
```

### 4.4 校验

必须校验：

- 表级行数一致。
- 核心字段非空。
- task 与 task_runs 外键完整。
- task_results 文件存在且路径在允许目录内。
- 报表记录数量与 legacy jobs 数量一致。
- 基础层事实表关键指标抽样一致。

示例校验：

```text
automation_tasks count == tasks count
automation_runs count == task_runs count
success runs with result_asset count == task_results count
users username set identical
fact_order_product row count identical by brand/platform/channel/date
```

金额校验：

- 使用 Decimal 文本或数据库 numeric。
- 不允许迁移脚本使用 float。
- 对销售额、订单金额等指标做按日汇总对比。

### 4.5 迁移演练

至少执行三次：

1. 本地开发库迁移演练。
2. 脱敏样例数据迁移演练。
3. 生产备份数据只读迁移演练。

每次输出：

```text
migration_report.md
row_count_summary.csv
validation_errors.csv
rollback_script.sql
```

## 5. Docker 部署关系

生产 Docker Compose 目标组件：

```text
app
postgres
redis
worker
```

### 5.1 app

职责：

- 提供 Web 页面和 API。
- 接收上传、任务提交、任务查询、结果下载。
- 不执行长耗时任务，长任务交给 worker。

环境变量：

```text
APP_ENV=production
DB_BACKEND=postgresql
DATABASE_URL=postgresql://...
REDIS_URL=redis://redis:6379/0
REPORT_TASK_MODE=task
```

### 5.2 postgres

职责：

- 保存用户、任务、报表、资产元数据、基础层事实表和维表。
- 提供事务、索引、备份、并发写入能力。

要求：

- 数据卷持久化。
- 开启每日备份。
- 不暴露公网端口。
- 只允许 app/worker 内网连接。

### 5.3 redis

职责：

- Celery broker。
- 可选任务短期状态缓存。

注意：

- Redis 不保存正式业务结果。
- Redis 丢失不应导致正式任务记录丢失。

### 5.4 worker

职责：

- 执行数据导入、报表生成、AI 内容生成等耗时任务。
- 通过 TaskRepository 读取任务。
- 通过 Service 层执行业务。
- 通过 TaskRepository/TaskResultRepository 写状态和结果。

部署建议：

```text
app: 2 replicas after first production phase
worker: 2-4 replicas depending on workload
postgres: 1 primary with backup
redis: 1 instance with persistence optional
```

### 5.5 网络关系

```text
browser/client
  -> nginx
  -> app
      -> postgres
      -> redis
  -> worker
      -> postgres
      -> redis
      -> external AI API
```

内部限制：

- app 和 worker 共享同一 DATABASE_URL。
- API Key 只通过环境变量或密钥管理注入。
- 不把 API Key 写入数据库、Excel、CSV、浏览器代码或日志。

## 6. 风险与回滚

### 6.1 主要风险

#### 数据一致性风险

风险：

- SQLite run message 中混有 JSON 和普通文本，迁移解析可能失败。
- task 状态由 latest run 推导，迁移时若 latest run 选择错误会影响页面展示。
- result_asset 路径可能指向不存在的本地文件。

控制：

- message 解析失败时保留为 `progress_json.legacy_message`。
- latest run 选择规则固定为 `ORDER BY id DESC`。
- 迁移后跑文件存在校验，缺失资产标记为不可下载。

#### 并发切换风险

风险：

- 切换期间 app 仍写 SQLite，PostgreSQL 数据落后。
- worker 和 app 读写不同数据库导致任务状态不一致。

控制：

- 切换窗口冻结任务提交。
- 最后一轮增量同步后再切换 `DB_BACKEND`。
- 切换后只允许 PostgreSQL 写入。

#### 权限风险

风险：

- `created_by` 当前用 `owner` 兼容，可能无法还原真实提交人。
- RBAC scope 尚未正式表结构化。

控制：

- 迁移期 `scope_snapshot_json` 明确标记来源为 legacy。
- 保留 `owner` 和 `created_by` 两个字段。
- 后续通过 RBAC 表逐步补齐正式授权。

#### 性能风险

风险：

- 任务列表、报表查询、基础层事实表如果索引不足，会拖慢页面。

控制：

- 迁移前按查询路径建索引。
- 用脱敏数据做 20 用户模拟测试。
- 事实表按 `brand_id/platform/channel/date` 建组合索引。

### 6.2 双写策略

建议灰度期不立刻双写所有业务表。

推荐顺序：

1. 只读影子库：SQLite 仍生产写入，PostgreSQL 每日同步，用于校验。
2. 任务模块双写：TaskRepository 写 SQLite + PostgreSQL，读仍走 SQLite。
3. 任务模块切读：读走 PostgreSQL，SQLite 保留回滚。
4. 全量切写：写走 PostgreSQL，SQLite 只保留备份。

双写注意：

- 每次写入使用同一 idempotency_key。
- 任一库写失败必须记录告警。
- 不允许静默忽略 PostgreSQL 写入失败。

### 6.3 灰度方案

Feature Flag：

```text
DB_BACKEND=sqlite|postgresql
TASK_DB_DUAL_WRITE=0|1
TASK_READ_BACKEND=sqlite|postgresql
```

阶段：

| 阶段 | 写入 | 读取 | 目标 |
|---|---|---|---|
| Phase 1 | SQLite | SQLite | 现状稳定 |
| Phase 2 | SQLite + PostgreSQL | SQLite | 验证双写 |
| Phase 3 | SQLite + PostgreSQL | PostgreSQL | 验证读切换 |
| Phase 4 | PostgreSQL | PostgreSQL | 正式切换 |

### 6.4 回滚方案

回滚条件：

- PostgreSQL 查询错误率升高。
- 报表结果与 SQLite 不一致。
- 任务状态丢失或错乱。
- 文件下载权限异常。

回滚动作：

1. 将 `TASK_READ_BACKEND` 切回 `sqlite`。
2. 将 `DB_BACKEND` 切回 `sqlite`。
3. 停止 worker 消费 PostgreSQL 任务。
4. 保留 PostgreSQL 数据用于排查，不删除。
5. 对切换期间 PostgreSQL 独有任务导出补偿清单。

禁止：

- 直接删除 PostgreSQL 数据。
- 无校验地把 PostgreSQL 数据覆盖回 SQLite。
- 回滚时重跑已成功的 AI 任务，避免重复费用。

### 6.5 数据一致性验收

切换前必须满足：

- 用户数一致。
- 任务数一致。
- 任务最近状态一致。
- 成功任务可下载资产数一致。
- P1 日报样例输出行数和核心金额一致。
- P2 AI 内容任务结果摘要可读取。
- 普通用户、Business Owner、Viewer 权限过滤一致。

## 7. 推荐实施顺序

1. 生成 PostgreSQL schema 草案和迁移 SQL，但不执行。
2. 新增 PostgreSQL Repository Adapter，保持接口不变。
3. 新增 Repository Factory，通过环境变量选择 Adapter。
4. 建立 SQLite 导出脚本和 PostgreSQL staging 导入脚本。
5. 用脱敏数据做迁移演练。
6. 建立双写和读切换 Feature Flag。
7. 先迁移 Task 模块，再迁移 Report/Asset 模块。
8. 最后迁移 Foundation 事实表和维表。
9. 通过 20 用户并发测试后，再进入生产切换。

## 8. 当前阶段结论

当前项目已经具备迁移 PostgreSQL 的基础边界：

- Service 层已逐步存在。
- Repository 接口已经定义。
- SQLite Adapter 已经隔离了一部分存储访问。
- TaskReadModel 已经补齐了权限和结果资产读取字段。

但还不应直接切库。下一步应先设计 schema SQL 和 PostgreSQL Adapter 骨架，并保持 SQLite 开发能力。生产切换必须经过脱敏数据迁移演练、双写灰度、读切换验证和可回滚方案确认。
