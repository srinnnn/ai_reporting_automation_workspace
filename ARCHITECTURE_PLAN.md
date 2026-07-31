# ARCHITECTURE_PLAN

生成日期：2026-07-30
当前阶段：阶段2 - 后端架构优化方案设计
输入依据：`PROJECT_REVIEW.md`
执行边界：本阶段只设计方案，不修改代码、不移动文件、不重构、不改变运行方式。
目标环境：Ubuntu + Docker Compose + 20+ 用户并发访问。

## 1. 当前架构问题总结

### 1.1 `app.py` 职责过重

当前 `intranet_app/app.py` 约 4755 行，已经同时承担了以下职责：

- HTTP Server 启动。
- GET/POST 路由分发。
- HTML 页面拼接。
- 登录态检查。
- 表单解析和文件上传读取。
- 数据入库业务编排。
- 日报、周报、月报生成编排。
- P2 内容生产和 AI 调用编排。
- 自动化任务执行。
- 文件下载和结果页面展示。

问题本质：

`app.py` 同时承担 Controller、View、Service、部分 Repository、文件处理和任务执行职责。继续堆功能会导致每次需求都触碰高风险文件，后续增加权限、异步任务、Docker 部署和 PostgreSQL 时回归风险会持续放大。

### 1.2 `storage.py` 职责混乱

当前 `intranet_app/storage.py` 约 1933 行，职责包括：

- SQLite 连接管理。
- 建表和 schema 升级。
- 用户、session、jobs、反馈、自动化任务存储。
- 基础数据层表结构定义。
- 基础层写入。
- 美团基础层读取。
- 部分数据转换和维度表 upsert。

问题本质：

`storage.py` 是 Repository、Migration、Schema Bootstrap、DAO、部分业务映射逻辑的混合体。它目前服务于本地 SQLite 是可接受的，但不适合迁移 PostgreSQL，也不适合支持多用户权限隔离和企业级审计。

### 1.3 同步任务阻塞

当前 Excel/CSV 上传、数据识别、数据清洗、基础层入库、报表生成、AI 生成都运行在 Web 请求线程内。

风险：

- Excel 文件较大时，上传和解析会阻塞请求。
- AI 调用依赖外部接口，网络慢或超时会占用请求线程。
- 报表生成失败后，用户难以知道任务是否已部分执行。
- 多人同时操作时，线程数、内存和 SQLite 写锁都会成为瓶颈。

### 1.4 SQLite 并发风险

当前数据库为本地 SQLite 文件：`intranet_app/runtime/intranet.sqlite3`。

SQLite 当前价值：

- 本地开发简单。
- 便于单机试运行。
- 无外部数据库依赖。

生产风险：

- 多用户并发写入容易触发 database locked。
- 缺少连接池。
- 表字段大量是 `TEXT`，查询和约束能力不足。
- 不适合长期沉淀多品牌、多渠道、大量报表和 AI 历史记录。

### 1.5 权限不足

当前认证基础具备密码哈希和 session token，但权限模型不足。

主要缺口：

- 无完整 RBAC 表结构。
- 无品牌、渠道、项目级数据授权。
- 无操作审计。
- session 缺少过期和清理机制。
- 后台任务没有权限上下文继承模型。

对于企业内部平台，权限不足是上线前必须解决的问题。

## 2. 目标架构设计

目标架构采用四层分离：

```text
Controller / API
        ↓
Service
        ↓
Repository
        ↓
Database
```

### 2.1 Controller / API 层

职责：

- 接收 HTTP 请求。
- 做基础参数解析和格式校验。
- 校验登录态和权限。
- 调用 Service。
- 返回 HTML、JSON、文件下载或任务状态。
- 不包含业务计算。
- 不直接访问数据库。
- 不直接调用 AI 模型。

未来建议目录：

```text
backend/api/
├── auth.py
├── dashboard.py
├── data_foundation.py
├── reports.py
├── ai_content.py
├── automation.py
└── admin.py
```

迁移原则：

初期可以保持 `intranet_app/app.py` 作为旧 Controller，但新业务逻辑不继续写入 `app.py`。后续逐步把路由迁移到 `backend/api/`。

### 2.2 Service 层

职责：

- 负责业务编排。
- 维护业务规则。
- 调用 Repository 读取/写入数据。
- 调用 processors 完成纯业务计算。
- 调用 AI Service 完成模型生成。
- 对外提供稳定的应用服务接口。

未来建议目录：

```text
backend/services/
├── auth_service.py
├── data_foundation_service.py
├── report_service.py
├── ai_service.py
├── ai_content_service.py
├── automation_service.py
├── file_service.py
└── permission_service.py
```

核心约束：

- P1/P2 Service 必须从统一基础数据层读取数据。
- 原始文件只允许进入 `DataFoundationService` 做 intake、识别、清洗、校验、入库。
- Report Service 不允许扫描 Downloads、runtime/intake 或原始上传目录兜底。

### 2.3 Repository 层

职责：

- 封装数据库读写。
- 隐藏 SQLite/PostgreSQL 差异。
- 管理事务边界。
- 提供按用户、品牌、平台、渠道、日期过滤的数据查询接口。
- 为后续 PostgreSQL 迁移提供接口稳定性。

未来建议目录：

```text
backend/repositories/
├── interfaces.py
├── sqlite/
│   ├── user_repository.py
│   ├── foundation_repository.py
│   ├── report_repository.py
│   └── task_repository.py
└── postgres/
    ├── user_repository.py
    ├── foundation_repository.py
    ├── report_repository.py
    └── task_repository.py
```

迁移原则：

先建立接口和 SQLite 实现，不立即迁移 PostgreSQL。这样能在不破坏当前本地运行能力的前提下，为 PostgreSQL 留出替换点。

### 2.4 Database 层

短期：

- 保留 SQLite。
- 不改变当前运行方式。
- 不迁移真实业务数据。

中期：

- 增加 PostgreSQL schema 设计。
- 增加 migration 工具。
- 新增 PostgreSQL Repository 实现。

长期：

- 云端使用 PostgreSQL。
- 本地开发可继续使用 SQLite 或 Docker PostgreSQL。
- 文件存储使用 volume，后续可替换对象存储。

## 3. 渐进式迁移方案

迁移原则：禁止一次性重构。每一步只改变一个边界，确保当前日报、周报、AI 选品仍可运行。

### Step 1：配置和启动层

目标：

把配置、运行目录、环境变量、启动入口从业务逻辑中拆出来，为 Docker 和多环境部署做准备。

建议动作：

- 新增 `backend/core/config.py`，定义环境变量读取、路径配置、运行模式。
- 新增 `backend/core/logging.py`，定义日志格式和日志级别。
- 新增 `backend/main.py` 作为未来启动入口。
- 保留 `intranet_app/app.py` 当前启动方式。
- 不改变默认端口和本地运行方式。

### Step 2：Repository 抽象

目标：

把数据库访问从 `storage.py` 中逐步抽象出来，为 PostgreSQL 迁移做准备。

建议动作：

- 新增 Repository interface。
- 先建立 SQLite Repository 包装现有 `AppStorage`。
- 不直接删除或重写 `storage.py`。
- 新业务优先调用 Repository 接口。

### Step 3：Data Foundation Service

目标：

把数据入库业务编排从 `app.py` 中拆出，但保留 `data_foundation.py` 的核心规则。

建议动作：

- 新增 `DataFoundationService`。
- 封装文件识别、字段映射、清洗、校验、保存校验报告、写入基础事实表。
- `app.py` 只负责接收上传和调用 Service。
- 保持基础层表和字段口径不变。

### Step 4：Report Service

目标：

把日报、周报、月报生成入口从 `app.py` 中拆出，保持 processors 业务口径不变。

建议动作：

- 新增 `ReportService`。
- 封装安踏美团日报、周报生成。
- 所有报表数据从 Foundation Repository 读取。
- 继续调用 `processors/anta_meituan_reporting.py`。
- 保留当前 CSV 输出。

### Step 5：AI Service

目标：

把 AI 网关和 P2 内容生产从 Web 请求处理逻辑中拆出。

建议动作：

- 新增 `AiService`，封装模型调用、超时、错误、重试策略、密钥读取。
- 新增 `AiContentService`，封装 P2 选品、Prompt 构造、AI 调用、质检和结果保存。
- 保留 `content_pipeline.py` 作为核心业务算法。
- 不改变现有百炼接口默认模型。

### Step 6：Async Worker

目标：

将耗时任务从同步请求改为后台任务。

建议动作：

- 引入 Redis + Celery。
- 新增任务表或扩展现有 `automation_runs/jobs`。
- API 创建任务后立即返回 task_id。
- Worker 执行上传处理、基础层入库、报表生成、AI 内容生成。
- 前端或 API 查询任务状态和下载结果。

### Step 7：PostgreSQL 迁移

目标：

云端主库升级为 PostgreSQL，解决并发写入、数据治理和查询性能问题。

建议动作：

- 设计 PostgreSQL schema。
- 增加 migration 工具。
- 实现 PostgreSQL Repository。
- 编写 SQLite 到 PostgreSQL 的迁移脚本。
- 保留 SQLite 本地开发能力。

## 4. 每阶段影响分析

### Step 1：配置和启动层

修改文件：

- 新增：`backend/core/config.py`
- 新增：`backend/core/logging.py`
- 新增：`backend/main.py`
- 可选新增：`backend/__init__.py`

影响范围：

- 仅影响未来启动方式和配置读取。
- 当前 `python -m intranet_app.app` 保持不变。

风险：

- 低。新增文件为主，不替换现有入口。

回滚方式：

- 删除新增 `backend/` 启动和配置文件即可。
- 当前 `intranet_app/app.py` 不受影响。

### Step 2：Repository 抽象

修改文件：

- 新增：`backend/repositories/interfaces.py`
- 新增：`backend/repositories/sqlite/user_repository.py`
- 新增：`backend/repositories/sqlite/foundation_repository.py`
- 新增：`backend/repositories/sqlite/report_repository.py`
- 新增：`backend/repositories/sqlite/task_repository.py`
- 少量修改：`intranet_app/app.py` 中低风险入口调用点。

影响范围：

- 影响数据库访问边界。
- 不改变 SQLite 表结构。
- 不改变已有数据。

风险：

- 中。接口设计不当会增加后续迁移成本。
- 需要保证现有测试覆盖所有被包装的方法。

回滚方式：

- `app.py` 调用点回退到 `AppStorage`。
- 删除或保留未使用 Repository 文件均可，不影响运行。

### Step 3：Data Foundation Service

修改文件：

- 新增：`backend/services/data_foundation_service.py`
- 可选新增：`backend/schemas/foundation.py`
- 少量修改：`intranet_app/app.py` 的 `/data-foundation/check` 和插件入库调用点。

影响范围：

- 数据上传入库流程。
- 美团插件同步后的自动入库。
- 基础层校验和事实表写入。

风险：

- 中高。该流程是 P1/P2 正式输出的数据源，必须保持字段口径不变。

回滚方式：

- 保留原 `_handle_data_foundation_check` 逻辑。
- 若 Service 迁移失败，路由调用回退到原 `build_ingestion_plan()` + `AppStorage` 流程。

### Step 4：Report Service

修改文件：

- 新增：`backend/services/report_service.py`
- 可选新增：`backend/schemas/reports.py`
- 少量修改：`intranet_app/app.py` 中日报、周报、月报生成入口。

影响范围：

- 安踏美团日报。
- 安踏美团周报。
- 历史安踏周报/月报入口。

风险：

- 中。不能改变当前日报/周报的计算口径和基础层读取规则。

回滚方式：

- 路由调用回退到现有 `_handle_anta_meituan_reporting_run()` 内部实现。
- processors 不动，因此业务计算可以直接恢复。

### Step 5：AI Service

修改文件：

- 新增：`backend/services/ai_service.py`
- 新增：`backend/services/ai_content_service.py`
- 可选新增：`backend/schemas/ai_content.py`
- 少量修改：`intranet_app/app.py` 的 `/p2-content-center/run` 和 AI 设置入口。

影响范围：

- 百炼连接测试。
- P2 内容生产。
- AI 选品、文案、视觉 Brief 生成。

风险：

- 中。AI 接口错误处理和返回 JSON 解析必须保持严格，禁止用模板冒充 AI 结果。

回滚方式：

- 路由调用回退到当前 `BailianClient` + `build_p2_content_pack()` 逻辑。
- `content_pipeline.py` 不动，业务输出可恢复。

### Step 6：Async Worker

修改文件：

- 新增：`backend/workers/celery_app.py`
- 新增：`backend/workers/file_tasks.py`
- 新增：`backend/workers/report_tasks.py`
- 新增：`backend/workers/ai_tasks.py`
- 修改：任务创建、任务状态查询、结果下载入口。
- 修改或扩展：任务表结构。

影响范围：

- 上传文件处理。
- 数据入库。
- 报表生成。
- AI 内容生产。
- 自动化任务页面。

风险：

- 高。引入 Redis/Celery 后运行链路变长，任务状态、失败重试、幂等性和结果一致性必须设计清楚。

回滚方式：

- 保留同步执行开关，例如 `TASK_MODE=sync|async`。
- 若 worker 不稳定，切回 `sync` 模式。
- 不删除原同步 processors。

### Step 7：PostgreSQL 迁移

修改文件：

- 新增：`backend/core/database.py`
- 新增：`backend/repositories/postgres/*`
- 新增：`migrations/`
- 新增：`scripts/migrate_sqlite_to_postgres.py`
- 修改：配置、Repository 工厂、Docker Compose。

影响范围：

- 所有数据库读写。
- 用户、权限、任务、报表、基础数据层。

风险：

- 高。涉及数据持久化和查询口径，必须分批迁移和双写/对账。

回滚方式：

- 保留 SQLite Repository。
- 配置开关：`DATABASE_BACKEND=sqlite|postgres`。
- PostgreSQL 迁移失败时切回 SQLite。
- 所有迁移脚本只新增或复制数据，不破坏本地 SQLite 文件。

## 5. 保留模块列表

以下模块短期明确不动，避免破坏现有业务流程：

### 5.1 必须暂时不动的业务计算模块

- `intranet_app/processors/anta_meituan_reporting.py`
- `intranet_app/processors/anta_reporting.py`
- `intranet_app/processors/bosch_sms.py`
- `intranet_app/processors/ai_selection.py`
- `intranet_app/processors/copy_content.py`
- `intranet_app/processors/anta_listing.py`
- `intranet_app/processors/anta_blacklist.py`

保留原因：

- 已有测试覆盖。
- 业务口径已经与当前日报、周报、AI 选品流程绑定。
- 这些模块多数是纯业务处理逻辑，适合被 Service 包装，而不是重写。

### 5.2 必须保留核心规则的模块

- `intranet_app/data_foundation.py`

保留原因：

- 它承载统一基础数据层的识别、映射、清洗、校验、品牌归属判断。
- 正式 P1/P2 输出依赖该规则闭环。
- 后续应外层服务化，而不是先重写内部规则。

### 5.3 暂时保留的运行模块

- `intranet_app/app.py`
- `intranet_app/storage.py`
- `intranet_app/auth.py`
- `intranet_app/ai_gateway.py`
- `browser_extensions/`
- `tools/`

保留原因：

- 当前系统仍需可运行。
- 第二阶段方案目标是低风险迁移，不是立刻切换框架。
- 浏览器插件仍是美团等无 API 场景的数据入口之一。

## 6. 云部署考虑

### 6.1 目标部署方式

目标：Ubuntu + Docker Compose。

建议服务：

```text
nginx
backend
worker
postgres
redis
```

部署原则：

- 一台服务器即可承载 MVP。
- 不依赖 GPU。
- 不依赖本地大模型。
- 不引入复杂微服务。
- AI 生成通过外部模型 API 完成。
- 文件存储先使用 Docker volume，后续可扩展对象存储。

### 6.2 服务器资源约束

最低配置：

- CPU：4 核。
- 内存：16GB RAM。
- 存储：200GB SSD。

推荐配置：

- CPU：8 核。
- 内存：32GB RAM。
- 存储：500GB SSD。

资源判断：

- 20+ 用户并发下，主要压力来自 Excel/CSV 解析、AI 请求等待、报表生成和数据库查询。
- 不使用本地大模型，因此 GPU 不是必要资源。
- 如果业务原始文件增长较快，SSD 容量和备份策略比 GPU 更重要。

### 6.3 Docker Compose 设计原则

未来 `docker-compose.yml` 应包含：

- `nginx`：反向代理、静态资源、上传大小限制、HTTPS 终止。
- `backend`：Web API 和页面服务。
- `worker`：Celery 后台任务。
- `postgres`：主数据库。
- `redis`：任务队列和缓存。

配置原则：

- 密钥通过 `.env` 注入，`.env` 不上传 Git。
- 提供 `.env.example` 模板。
- 上传文件、结果文件、日志使用 volume。
- PostgreSQL 使用持久化 volume。
- Redis 不暴露公网端口。
- backend 不直接暴露公网，由 nginx 代理。
- 增加 `/healthz` 健康检查。

### 6.4 不依赖项

方案明确不依赖：

- GPU。
- 本地大模型。
- Kubernetes。
- 多服务复杂微服务架构。
- 平台后台 API 必须可用。

对于美团、京东、天猫等可能没有 API 的平台，数据入口仍以浏览器插件、标准导出模板、人工上传和后续页面采集方案为主。

## 7. 验收标准

本架构方案以及后续实施必须满足以下标准：

### 7.1 业务不破坏

- 不破坏安踏美团日报。
- 不破坏安踏美团周报。
- 不破坏 AI 选品。
- 不破坏 P2 内容生产中心。
- 不破坏博西短彩信处理。
- 不破坏安踏上下架、素材筛选、黑名单筛选。

### 7.2 数据规则不破坏

- P1/P2 正式输出必须从统一基础数据层读取。
- 原始 Excel/CSV 只能作为 intake、校验、回填、诊断或测试输入。
- 报表入口不能直接扫描 Downloads、runtime/intake 或 raw_data 兜底。
- 缺基础层数据时必须失败闭环并提示补数。

### 7.3 本地开发能力保留

- 保留 SQLite 开发能力。
- 保留 `python -m intranet_app.app` 本地启动能力，直到新启动方式通过验收。
- 保留当前 samples 和 tests。
- 保留浏览器插件半自动导出能力。

### 7.4 未来 PostgreSQL 支持

- Repository 层必须能切换 SQLite/PostgreSQL 实现。
- 业务 Service 不应直接依赖 SQLite 连接。
- 数据表设计必须支持多用户、品牌、平台、渠道、项目隔离。
- 迁移脚本不得破坏本地 SQLite 数据。

### 7.5 Redis/Celery 扩展支持

- 耗时任务必须能从同步调用迁移到异步任务。
- 任务必须有状态：pending、running、success、failed、cancelled。
- 任务结果必须可追溯到用户、品牌、渠道、项目和源文件批次。
- 异步任务失败后必须可重试，重复执行必须尽量幂等。

## 8. 推荐执行顺序

建议后续进入实施时按以下顺序推进：

1. 新增架构骨架和配置层，不接管业务流量。
2. Repository 抽象先包一层 SQLite，不改数据库。
3. Data Foundation Service 接管入库编排。
4. Report Service 接管日报/周报编排。
5. AI Service 和 AI Content Service 接管 P2 编排。
6. 引入异步任务，但保留同步 fallback。
7. 设计并实现 PostgreSQL schema。
8. 增加 Docker Compose。
9. 做 20 用户性能测试。

## 9. 阶段结论

本阶段建议采用“外层包裹、逐步替换”的低风险升级路线。

不要第一步就拆散 `app.py` 或重写 processors。正确做法是先建立 Service/Repository 边界，让旧代码继续稳定运行；等边界稳定后，再逐步把 `app.py` 中的业务编排迁移出去。

该方案能同时满足：

- 不破坏日报。
- 不破坏 AI 选品。
- 保留 SQLite 开发能力。
- 支持未来 PostgreSQL。
- 支持 Redis/Celery 扩展。
- 支持 Ubuntu + Docker Compose 部署。
- 面向 20+ 用户并发做稳定性、安全性和可维护性升级。

第二阶段方案设计完成。等待确认后，下一步应进入“Step 1：配置和启动层”的具体实施设计与小步代码改造。
