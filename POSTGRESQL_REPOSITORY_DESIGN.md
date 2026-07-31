# POSTGRESQL_REPOSITORY_DESIGN

生成日期：2026-07-31

当前阶段：Step 7-C - PostgreSQL Repository Adapter Design

执行边界：本阶段只生成设计文档，不修改代码、不连接数据库、不执行 SQL。

## 1. 当前 Repository 接口分析

当前 Repository 抽象定义在 `backend/repositories/interfaces.py`。

核心接口：

```text
UserRepository
FoundationRepository
ReportRepository
TaskRepository
```

当前 SQLite Adapter 位于：

```text
backend/repositories/sqlite/
```

现阶段设计原则：

- 第一阶段 PostgreSQL Adapter 必须实现现有接口。
- Service 层不修改 import、不修改方法调用、不感知 SQLite/PostgreSQL。
- PostgreSQL Adapter 可以内部读写新 schema，但返回值必须兼容当前 dataclass。
- 不在本阶段新增真实数据库连接代码。

### 1.1 UserRepository

当前接口：

```python
create_user(request: UserCreate) -> UserRecord
get_user(username: str) -> UserRecord | None
verify_user(username: str, password: str) -> bool
```

当前 SQLite 行为：

- `create_user()` 目前只支持 legacy default admin。
- `get_user()` 返回 `UserRecord`。
- `verify_user()` 使用 `verify_password()` 校验 `PasswordHash`。

PostgreSQL 设计目标：

- 支持创建任意用户，而不是只支持 admin。
- 密码仍使用现有 `PasswordHash` 结构和校验函数。
- 第一阶段保留 `users.role` 文本字段，后续 RBAC 再拆表。
- 返回值仍为 `UserRecord`，避免登录、session、PermissionService 受影响。

### 1.2 FoundationRepository

当前接口：

```python
save_foundation_check(record: FoundationCheckRecord) -> None
save_foundation_rows(import_batch_id: str, plan: Any) -> None
query_foundation_rows(brand_id, platform, channel, file_type) -> list[dict[str, str]]
```

当前 SQLite 行为：

- 通过 `AppStorage.save_foundation_check()` 保存导入校验。
- 通过 `AppStorage.save_foundation_fact_rows()` 写事实表。
- 通过 `AppStorage.load_meituan_foundation_rows()` 查询基础层数据。

PostgreSQL 设计目标：

- 第一阶段保留现有 fact/dim 表语义。
- `query_foundation_rows()` 返回 `list[dict[str, str]]`，保持 ReportService/AIContentService 不变。
- 写入必须使用事务，导入批次、源文件、校验报告、事实表写入必须一致。
- Foundation 最后迁移，因为它涉及事实表最多、业务口径风险最高。

### 1.3 ReportRepository

当前接口：

```python
save_report(request: ReportCreate) -> int
get_report(report_id: int) -> JobRecord | None
```

当前 SQLite 行为：

- 通过 legacy `jobs` 保存报表文件。
- 返回 `JobRecord`。

PostgreSQL 设计目标：

- 写 `reports` + `assets`，但第一阶段 `get_report()` 仍返回 `JobRecord` 兼容旧下载逻辑。
- 报表文件不存数据库二进制，只存资产元数据。
- `summary/warnings` 写入 JSONB。
- Report 迁移排在 Task 之后。

### 1.4 TaskRepository

当前接口：

```python
create_task(request: AutomationTaskCreate) -> int
update_task_status(task_id: int, status: str) -> None
get_task(task_id: int) -> AutomationTaskRecord | None
save_task_result(request: TaskRunCreate) -> int
list_tasks() -> list[AutomationTaskRecord]
list_task_runs(limit: int = 200) -> list[AutomationRunRecord]
```

当前 SQLite 行为：

- `create_task()` 写 `automation_tasks`。
- `update_task_status()` 对 enabled/disabled 调整任务启用状态，对 pending/running/success/failed/cancelled 写一条 `automation_runs`。
- `save_task_result()` 写一条 `automation_runs.message`，兼容 result JSON 或 error 文本。
- `list_tasks()` 返回所有 `AutomationTaskRecord`。
- `list_task_runs()` 返回最近 run。

PostgreSQL 设计目标：

- Task 优先迁移。
- PostgreSQL 内部写正式 `tasks/task_runs/task_results/assets`。
- 第一阶段仍返回 `AutomationTaskRecord/AutomationRunRecord`，让 `TaskQueryService` 不改。
- 后续再新增正式 Task DTO 和 read model 查询接口。

## 2. PostgreSQL Adapter 结构设计

建议新增目录：

```text
backend/repositories/postgresql/
  __init__.py
  connection.py
  user_repository.py
  foundation_repository.py
  report_repository.py
  task_repository.py
```

### 2.1 connection.py

职责：

- 管理 PostgreSQL 连接池。
- 提供事务上下文。
- 统一处理参数化 SQL 执行。
- 屏蔽具体驱动差异。

建议暴露概念接口：

```python
class PostgreSQLConnectionProvider:
    def connection(self): ...
    def transaction(self): ...
```

设计要求：

- 从 `DATABASE_URL` 读取连接字符串。
- 生产环境使用连接池，不使用每请求新建连接。
- 默认连接时区使用 UTC 或服务器统一时区，业务展示层再格式化。
- 所有 SQL 必须参数化。
- 不在日志中输出连接串、密码或 SQL 参数中的敏感字段。

驱动选择建议：

```text
psycopg 3
```

原因：

- 支持现代 PostgreSQL。
- JSONB、事务、连接池能力成熟。
- Python 社区维护活跃。

注意：本阶段只设计，不安装依赖、不写真实连接代码。

### 2.2 user_repository.py

类名建议：

```python
PostgreSQLUserRepository(UserRepository)
```

方法映射：

| 接口方法 | PostgreSQL 表 | 说明 |
|---|---|---|
| create_user | users | 写用户和密码摘要 |
| get_user | users | 根据 username 查询 |
| verify_user | users | 取 password_salt/password_digest 后调用现有 verify_password |

返回兼容：

```text
users row -> UserRecord
password_salt/password_digest -> PasswordHash
```

事务要求：

- `create_user()` 单事务。
- username 唯一冲突返回明确错误，不静默覆盖。

### 2.3 foundation_repository.py

类名建议：

```python
PostgreSQLFoundationRepository(FoundationRepository)
```

方法映射：

| 接口方法 | PostgreSQL 表 | 说明 |
|---|---|---|
| save_foundation_check | import_batches/source_files/validation_reports/missing_data_items | 保存导入检查 |
| save_foundation_rows | fact/dim tables | 保存清洗后的基础层数据 |
| query_foundation_rows | fact/dim tables | 查询正式 P1/P2 基础数据 |

设计要求：

- 一次导入批次必须事务化。
- 事实表写入需要幂等键，避免同一批次重复写入脏数据。
- 查询必须按 `brand_id/platform/channel/file_type/date` 使用索引。
- 返回 `dict[str, str]` 兼容现有 ReportService 和 AIContentService。

迁移注意：

- Foundation 表数量多、字段口径复杂，排最后迁移。
- 在完全验证前，禁止让正式报表绕过基础数据层直接查 raw 文件。

### 2.4 report_repository.py

类名建议：

```python
PostgreSQLReportRepository(ReportRepository)
```

方法映射：

| 接口方法 | PostgreSQL 表 | 说明 |
|---|---|---|
| save_report | assets + reports | 先保存文件资产元数据，再保存报表记录 |
| get_report | reports + assets | 组合返回 legacy `JobRecord` |

设计要求：

- 文件本体仍由 ResultAssetService 或文件存储层负责。
- PostgreSQL 只保存 `storage_path/public_path/filename/size/checksum`。
- `summary` 写 `summary_json`。
- `warnings` 写 `warnings_json`。

兼容策略：

- `ReportCreate.brand` 迁移期映射到 `reports.brand_name` 或 `brand_id`，具体由调用方现有输入决定。
- `JobRecord.input_file/result_file` 需要从 assets 恢复成 `Path`。

### 2.5 task_repository.py

类名建议：

```python
PostgreSQLTaskRepository(TaskRepository)
```

方法映射：

| 接口方法 | PostgreSQL 表 | 说明 |
|---|---|---|
| create_task | tasks | 创建任务主记录 |
| update_task_status | tasks + task_runs | 更新当前状态并追加 run |
| get_task | tasks | 返回兼容 `AutomationTaskRecord` |
| save_task_result | task_runs + task_results + assets | 保存执行结果 |
| list_tasks | tasks | 返回兼容任务列表 |
| list_task_runs | task_runs | 返回兼容 run 列表 |

关键映射：

```text
AutomationTaskCreate.file_type -> tasks.task_type
AutomationTaskCreate.owner -> tasks.owner
AutomationTaskCreate.owner -> tasks.created_by，迁移期兼容
AutomationTaskCreate.date_window -> tasks.payload_json.date_window
AutomationTaskCreate.frequency/scheduled_time/notes -> tasks.payload_json legacy fields
```

兼容返回：

```text
tasks row -> AutomationTaskRecord
task_runs row -> AutomationRunRecord
```

`AutomationTaskRecord` 字段还原：

| AutomationTaskRecord | PostgreSQL 来源 |
|---|---|
| id | tasks.id |
| task_name | tasks.task_name |
| business_unit | tasks.business_unit |
| brand_id | tasks.brand_id |
| brand_name | tasks.brand_name |
| platform | tasks.platform |
| channel | tasks.channel |
| file_type | tasks.task_type |
| frequency | payload_json.frequency |
| scheduled_time | payload_json.scheduled_time |
| date_window | payload_json.date_window |
| enabled | tasks.status != cancelled |
| output_folder | tasks.output_folder |
| owner | tasks.owner |
| notes | payload_json.notes |
| created_at | tasks.created_at |
| updated_at | tasks.updated_at |

`AutomationRunRecord` 字段还原：

| AutomationRunRecord | PostgreSQL 来源 |
|---|---|
| id | task_runs.id |
| task_id | task_runs.task_id |
| task_name | tasks.task_name |
| run_date | progress_json.run_date or system |
| status | task_runs.status |
| downloaded_file_count | progress_json.downloaded_file_count default 0 |
| synced_file_count | progress_json.synced_file_count default 0 |
| message | error_message or progress_json legacy/result summary |
| executed_by | task_runs.worker_id or progress_json.executed_by |
| created_at | task_runs.created_at |

## 3. SQLite Adapter 迁移策略

目标：Service 层不修改。

当前调用：

```text
Service
  -> UserRepository/FoundationRepository/ReportRepository/TaskRepository
  -> SQLite Adapter
```

迁移后：

```text
Service
  -> same Repository interface
  -> SQLite Adapter or PostgreSQL Adapter
```

策略：

1. 保留所有 SQLite Adapter。
2. 新增 PostgreSQL Adapter，不替换旧文件。
3. 通过 Repository Factory 选择具体实现。
4. Service 构造处逐步改为从 Factory 获取 Repository。
5. `DB_BACKEND=sqlite` 时行为保持当前一致。
6. `DB_BACKEND=postgresql` 只在测试通过后进入灰度。

关键要求：

- 不改 `processors/`。
- 不改报表计算口径。
- 不改数据基础层字段规则。
- 不让 Service 直接 import PostgreSQL。

## 4. Repository Factory 设计

建议新增：

```text
backend/repositories/factory.py
```

配置：

```text
DB_BACKEND=sqlite|postgresql
DATABASE_URL=postgresql://...
SQLITE_DB_PATH=runtime/app.db
```

设计接口：

```python
class RepositoryFactory:
    def user_repository(self) -> UserRepository: ...
    def foundation_repository(self) -> FoundationRepository: ...
    def report_repository(self) -> ReportRepository: ...
    def task_repository(self) -> TaskRepository: ...
```

选择规则：

```text
DB_BACKEND=sqlite
  -> SQLite adapters backed by AppStorage

DB_BACKEND=postgresql
  -> PostgreSQL adapters backed by connection provider
```

非法配置：

- 生产环境 `DB_BACKEND` 缺失：fail closed。
- 生产环境 `DB_BACKEND=sqlite`：允许启动前检查失败，除非显式 `ALLOW_SQLITE_IN_PRODUCTION=1`。
- `DB_BACKEND=postgresql` 但缺少 `DATABASE_URL`：启动失败。

灰度扩展：

```text
TASK_READ_BACKEND=sqlite|postgresql
TASK_DB_DUAL_WRITE=0|1
```

这些不应进入第一版 Factory 主路径，避免一次性复杂化。

## 5. 数据类型映射

### 5.1 datetime

SQLite 当前：

- 多数时间字段是字符串。
- 格式多为 ISO 字符串。

PostgreSQL：

```text
TIMESTAMPTZ
```

映射规则：

- 写入时统一转换为 timezone-aware datetime。
- 读取后对当前 dataclass 兼容返回 ISO 字符串。
- 后续正式 DTO 再使用 datetime 类型。

注意：

- 不在数据库里存本地展示格式。
- 页面展示层负责格式化。

### 5.2 JSON

SQLite 当前：

- JSON 以 TEXT 保存，如 `automation_runs.message`。

PostgreSQL：

```text
JSONB
```

映射规则：

- `payload_json/scope_snapshot_json/progress_json/summary_json/metadata_json` 使用 dict/list 写入。
- 进入 Repository 前由 dataclass 或 Service 校验结构。
- 读取时转为 Python dict/list。
- 兼容旧接口时可重新序列化为 JSON 字符串。

### 5.3 Decimal

SQLite 当前：

- 很多金额字段以 text 或 CSV 字符串流转。

PostgreSQL：

```text
NUMERIC(p, s)
```

第一阶段：

- Repository 内不把金额转 float。
- 若现有接口返回 `dict[str, str]`，继续用字符串返回。
- 未来 Foundation 正式表可使用 `NUMERIC(18, 4)`。

### 5.4 Boolean

SQLite 当前：

```text
INTEGER 0/1
```

PostgreSQL：

```text
BOOLEAN
```

映射规则：

- `AutomationTaskRecord.enabled` 读取为 bool。
- `tasks.status='cancelled'` 可映射为 `enabled=False`。
- 后续如果需要独立启用字段，可新增 `enabled BOOLEAN`，但 Step 7-B schema 暂不引入。

### 5.5 Enum

当前：

```text
TASK_STATUSES = ("pending", "running", "success", "failed", "cancelled")
```

PostgreSQL 第一阶段：

```text
TEXT + CHECK
```

原因：

- 迁移和回滚比 PostgreSQL native enum 更简单。
- 与现有 Python 字符串状态兼容。

后续可选：

- 当状态集合长期稳定后，再迁移为 native enum。

## 6. 迁移顺序

要求顺序：

```text
Task 优先
Report 其次
Foundation 最后
```

### 6.1 Phase 1: TaskRepository

原因：

- Task 模块已经有 Repository、TaskService、TaskQueryService、TaskResultService。
- 任务状态是未来 Celery 的基础。
- 数据范围相对小，便于验证。

验收：

- `create_task()` 返回 task_id。
- `update_task_status()` 更新 `tasks.status` 并写 `task_runs`。
- `save_task_result()` 能写 run 和 result asset。
- `list_tasks()` 与 SQLite 返回字段一致。
- `TaskQueryService` 输出一致。
- `/tasks` 和 `/api/tasks/<id>` 行为一致。

### 6.2 Phase 2: ReportRepository

原因：

- 报表结果依赖 assets。
- ReportRepository 写入量较小，适合在 Task 后迁移。

验收：

- `save_report()` 写 `assets/reports`。
- `get_report()` 返回兼容 `JobRecord`。
- legacy job 下载流程不受影响。
- Task 模式结果文件和 Report 交付文件不会混淆。

### 6.3 Phase 3: UserRepository

原因：

- 用户权限影响面大，但表结构简单。
- 可以先在测试环境迁移用户。

验收：

- admin 登录不变。
- 密码校验不变。
- role 文本兼容 PermissionService。
- 不暴露密码摘要。

### 6.4 Phase 4: FoundationRepository

原因：

- 基础数据层涉及正式业务口径。
- 事实表多，字段映射复杂，必须最后迁移。

验收：

- 同一品牌、平台、渠道、日期下，SQLite 与 PostgreSQL 查询行数一致。
- 日报、周报、P2 AI 选品从 PostgreSQL 基础层生成结果一致。
- 金额字段按 Decimal/NUMERIC 校验一致。
- 缺失数据仍 fail closed。

## 7. 风险

### 7.1 事务风险

风险：

- Task 结果保存需要同时写 `task_runs/task_results/assets/tasks.status`。
- 任一写入失败都可能导致状态和结果不一致。

控制：

- Repository 方法使用单事务。
- 任务状态更新和结果资产写入必须原子化。
- 异常时 rollback，并返回明确错误。

### 7.2 连接池风险

风险：

- 20+ 用户同时访问、上传、查任务，若每次新建连接会拖慢系统。
- 连接泄漏会耗尽 PostgreSQL 连接数。

控制：

- 使用连接池。
- 每个请求/任务使用上下文管理器释放连接。
- Worker 和 app 分开配置池大小。
- 设置 statement timeout，避免长查询拖垮连接池。

### 7.3 SQL 差异风险

差异点：

- SQLite `?` 参数占位 vs PostgreSQL `%s` 或 named 参数。
- SQLite TEXT JSON vs PostgreSQL JSONB。
- SQLite INTEGER bool vs PostgreSQL BOOLEAN。
- SQLite datetime text vs PostgreSQL TIMESTAMPTZ。
- SQLite `lastrowid` vs PostgreSQL `RETURNING id`。

控制：

- SQL 只在 Adapter 内部。
- Service 不写 SQL。
- Adapter 测试覆盖所有接口方法。

### 7.4 性能风险

风险：

- 如果 `list_tasks()` 继续全表返回，再由 Python 过滤，数据量变大后会慢。
- Foundation 查询如果缺少组合索引，会影响日报/周报。

控制：

- PostgreSQL Adapter 第一阶段保留接口，但内部可以分页和限制默认返回。
- 后续新增过滤接口替代全表 list。
- 对 Task 和 Report 按权限过滤字段建立组合索引。
- Foundation 查询按 `brand_id/platform/channel/date` 建索引。

### 7.5 数据兼容风险

风险：

- PostgreSQL Adapter 返回 dataclass 时字段格式不一致会影响测试和页面。
- `created_at/updated_at` 从 datetime 变为字符串时格式可能改变。

控制：

- Adapter 层统一输出 ISO 字符串。
- 保持 `AutomationTaskRecord/AutomationRunRecord/UserRecord/JobRecord` 构造规则。
- 迁移前用现有 unittest 全量跑一遍。

### 7.6 安全风险

风险：

- DATABASE_URL 泄露。
- SQL 日志包含用户或业务敏感信息。
- 文件 `storage_path` 直接暴露。

控制：

- 不打印 DATABASE_URL。
- SQL 日志只打 query name，不打参数。
- 下载仍通过 TaskResultService/ResultAssetService 做路径校验。
- API Key 不写数据库。

## 8. Adapter 测试设计

第一阶段建议使用测试替身或本地临时 PostgreSQL 容器，但本阶段不执行。

未来测试覆盖：

```text
test_postgresql_user_repository.py
test_postgresql_task_repository.py
test_postgresql_report_repository.py
test_postgresql_foundation_repository.py
```

测试重点：

- 接口返回类型与 SQLite Adapter 一致。
- 事务失败 rollback。
- JSONB 字段读写一致。
- datetime 输出兼容。
- Decimal 不转 float。
- 状态 CHECK 违规时错误明确。
- 任务结果资产路径不直接暴露。

## 9. 当前阶段结论

PostgreSQL Adapter 可以在不修改 Service 层的前提下渐进引入。最稳妥路径是：

1. 先新增 PostgreSQL 目录和设计。
2. 再实现连接提供者和 TaskRepository Adapter。
3. 用 Factory 做 `DB_BACKEND` 切换。
4. Task 通过后迁移 Report。
5. 用户登录验证稳定后迁移 User。
6. 最后迁移 Foundation。

当前不应直接写真实连接代码。下一步可以先做 `Repository Factory Design` 或 `PostgreSQL TaskRepository Adapter Skeleton`，但 Skeleton 也应避免连接真实数据库，先用接口和测试替身验证边界。
