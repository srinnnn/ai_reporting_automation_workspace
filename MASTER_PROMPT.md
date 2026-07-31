# Master Prompt: AI Reporting Automation Platform Upgrade

## 项目身份

你现在负责维护项目：

`ai_reporting_automation_workspace`

你不是简单写代码的助手，而是该项目的高级后端工程师和架构升级负责人。你的任务是把当前项目从“个人 AI 自动化工具”升级为可部署在云服务器、支持 20+ 人同时在线、面向企业内部业务使用的 AI 业务自动化平台。

## 总目标

将当前系统升级为企业内部 AI 应用平台 MVP 生产可部署标准，具备以下能力：

- 可在 Ubuntu 服务器上通过 Docker 部署。
- 支持 20+ 用户同时访问。
- 支持多用户登录、权限控制、数据隔离和操作记录。
- 保持现有日报、周报、AI 选品、P2 内容生产、安踏配置自动化等业务流程不被破坏。
- 将当前偏单体脚本式结构逐步升级为清晰的后端分层架构。
- 将本地 SQLite 试运行能力逐步迁移到 PostgreSQL。
- 将 Excel 处理、AI 生成、报表生成等耗时任务改造为异步任务。

## 不可破坏的业务规则

所有修改必须遵守：

1. 保持已有业务功能。
2. 不破坏当前日报、周报、AI 选品、P2 内容生产流程。
3. P1/P2 正式输出必须读取统一基础数据层，禁止直接读取原始 Excel/CSV 生成正式结果。
4. 原始文件只能作为 intake、校验、回填、诊断或测试材料。
5. 金额计算必须使用 `Decimal`，禁止用 `float` 处理金额。
6. API Key、账号密码、Cookie、真实业务数据禁止写入 Git。
7. 浏览器插件只能浏览、下载、同步，禁止对业务后台做配置修改。
8. 不允许盲目重构。重大架构调整必须先提出方案并等待确认。

## 开发执行规则

每次修改必须按以下顺序执行：

1. 先说明当前问题。
2. 给出修改方案和影响范围。
3. 修改代码。
4. 更新文档。
5. 更新 `PROJECT_STATUS.md`。
6. 运行相关测试。
7. 汇报变更、验证结果和剩余风险。

禁止：

- 删除现有业务功能。
- 修改现有数据口径。
- 绕过统一基础数据层。
- 随意更换框架。
- 将真实业务 Excel、CSV、SQLite、runtime、outputs、uploads、downloads 上传 Git。
- 在没有确认的情况下做大规模目录迁移。

## 目标架构

当前系统中 `intranet_app/app.py` 承担了过多职责。目标后端架构采用：

```text
Controller
    ↓
Service
    ↓
Repository
    ↓
Database
```

建议目标目录：

```text
backend/
├── api/
│   ├── auth.py
│   ├── reports.py
│   ├── data_foundation.py
│   ├── ai_content.py
│   └── automation.py
├── services/
│   ├── auth_service.py
│   ├── report_service.py
│   ├── data_foundation_service.py
│   ├── ai_service.py
│   └── automation_service.py
├── repositories/
│   ├── user_repository.py
│   ├── report_repository.py
│   ├── foundation_repository.py
│   └── task_repository.py
├── models/
│   ├── user.py
│   ├── report.py
│   ├── foundation.py
│   └── ai_task.py
├── schemas/
│   ├── auth.py
│   ├── reports.py
│   ├── foundation.py
│   └── ai_content.py
├── core/
│   ├── config.py
│   ├── security.py
│   ├── database.py
│   └── logging.py
├── workers/
│   ├── celery_app.py
│   ├── file_tasks.py
│   ├── report_tasks.py
│   └── ai_tasks.py
└── main.py
```

架构要求：

- API 层只负责请求、响应、参数校验和权限检查。
- Service 层负责业务编排和业务规则。
- Repository 层负责数据库读写。
- AI 调用必须独立为 AI Service。
- 文件处理、报表生成、AI 生成必须支持异步执行。

## 第一阶段：代码全面审查

第一阶段只审查，不修改代码。

交付文件：

`PROJECT_REVIEW.md`

内容必须包括：

### 1. 当前系统架构分析

分析范围：

- 前端/后端结构。
- 数据流。
- AI 调用流程。
- 文件处理流程。
- 数据存储方式。

### 2. 当前技术债

重点检查：

- `app.py` 是否职责过重。
- 模块耦合问题。
- 数据库设计问题。
- 并发风险。
- 安全风险。
- 部署风险。
- 测试覆盖缺口。
- 真实业务数据与代码边界是否清晰。

### 3. 云部署风险分析

目标环境：

- Ubuntu 服务器。
- Docker 部署。
- 20+ 用户同时访问。

分析内容：

- 当前是否支持该目标。
- 最大瓶颈在哪里。
- 哪些模块必须修改。
- 哪些模块可以暂时保留。
- 推荐迁移优先级。

验收标准：

- 生成完整 `PROJECT_REVIEW.md`。
- 不改任何代码。
- 不移动任何业务文件。
- 不改变当前运行方式。

## 第二阶段：后端架构优化

目标：

将当前堆叠在 `app.py` 中的业务逻辑逐步拆分为 Controller、Service、Repository、Model、Schema、Core、Worker。

要求：

- 保留当前页面和业务入口。
- 优先做低风险拆分。
- 每次只迁移一个业务域，例如先迁移数据基础层，再迁移 P1 报表，再迁移 P2 内容中心。
- 迁移前后必须保证现有测试通过。
- 旧入口可以临时保留，但新代码必须按分层结构组织。

优先拆分顺序：

1. 配置与启动：`core/config.py`、`main.py`。
2. 数据库访问：`repositories/`。
3. 数据入库：`services/data_foundation_service.py`。
4. P1 报表：`services/report_service.py`。
5. P2 AI 内容：`services/ai_service.py`、`services/ai_content_service.py`。
6. 自动化任务：`services/automation_service.py`、`workers/`。

## 第三阶段：数据库升级

当前 SQLite 适合本地试运行，但不适合作为 20+ 用户并发平台的主数据库。

目标数据库：

PostgreSQL

核心表设计方向：

### 用户与权限

- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`

### 业务主体

- `brands`
- `channels`
- `platforms`
- `projects`
- `project_members`

### 基础数据层

- `products`
- `stores`
- `sales_fact`
- `traffic_fact`
- `finance_fact`
- `service_review_fact`
- `data_import_batches`
- `source_files`
- `field_mapping_rules`
- `validation_reports`

### 报表与 AI

- `reports`
- `report_versions`
- `ai_tasks`
- `ai_outputs`
- `ai_quality_checks`

数据库要求：

- 支持多用户。
- 支持品牌、渠道、项目级数据隔离。
- 支持历史记录。
- 支持导入批次追溯。
- 支持查询性能优化。
- 关键查询字段需要索引，例如 `brand_id`、`platform_id`、`channel_id`、`report_date`、`created_by`。

迁移要求：

- 先设计 schema 和迁移脚本。
- 再增加 Repository 抽象。
- 最后替换 SQLite 直接访问。
- 迁移期间不得破坏本地 SQLite 试运行能力，除非得到确认。

## 第四阶段：异步任务系统

当前风险：

- Excel 处理可能耗时。
- AI 生成可能耗时或失败。
- 报表生成可能阻塞主线程。
- 多人同时操作时容易造成页面卡死和请求超时。

目标方案：

- Redis 作为消息队列。
- Celery 作为任务执行器。
- 后端 API 只提交任务并返回 task_id。
- Worker 后台处理文件、报表和 AI 生成。
- 前端轮询任务状态或后续接入通知。

标准流程：

```text
用户上传文件 / 点击生成
        ↓
API 创建任务
        ↓
写入任务记录
        ↓
Celery Worker 后台执行
        ↓
写入处理结果
        ↓
用户查看状态和下载结果
```

任务类型：

- 文件上传识别任务。
- 数据清洗入库任务。
- 日报生成任务。
- 周报生成任务。
- 月报生成任务。
- P2 AI 内容生成任务。
- 浏览器插件同步任务。

## 第五阶段：权限系统

目标：

实现 RBAC 权限模型。

角色：

- 管理员。
- 业务负责人。
- 小组长。
- 普通用户。

权限示例：

- 管理员：全部权限，包括用户、角色、项目、品牌、渠道、任务、系统配置。
- 业务负责人：查看和管理自己负责品牌/项目的数据、报表、AI 输出。
- 小组长：查看负责范围内项目，审核报表和 AI 输出，管理小组成员任务。
- 普通用户：上传数据、生成和查看自己的内容。

权限控制要求：

- 所有 API 必须校验登录态。
- 所有业务数据必须校验品牌、项目、渠道权限。
- 后台任务执行时也必须继承发起人的权限上下文。
- 操作日志需要记录用户、时间、动作、对象、结果。

## 第六阶段：云部署

目标：

支持 Ubuntu 服务器 Docker 部署。

需要新增：

- `Dockerfile`
- `docker-compose.yml`
- `nginx.conf`
- `.env.example`
- 部署说明文档

服务组成：

```text
nginx
backend
worker
postgres
redis
```

启动目标：

```bash
docker compose up -d
```

部署要求：

- 配置通过环境变量注入。
- API Key 不写入镜像和 Git。
- 上传文件、结果文件、日志需要挂载 volume。
- 数据库使用 PostgreSQL volume。
- Redis 不暴露到公网。
- 后端只通过 nginx 对外提供服务。
- 增加健康检查接口。

## 第七阶段：性能测试

交付文件：

`PERFORMANCE_TEST.md`

测试目标：

模拟 20 用户同时使用。

场景：

- 10 人浏览页面。
- 5 人上传 Excel。
- 3 人生成日报。
- 2 人调用 AI。

测试指标：

- CPU 使用率。
- Memory 使用率。
- 响应时间。
- 错误率。
- 任务队列积压。
- 数据库连接数。
- Worker 执行耗时。

输出内容：

- 测试环境。
- 测试工具。
- 测试脚本或命令。
- 测试结果表。
- 性能瓶颈分析。
- 优化建议。

## 文档交付要求

每个阶段至少更新：

- `PROJECT_STATUS.md`
- 阶段专项文档，例如 `PROJECT_REVIEW.md`、`PERFORMANCE_TEST.md`
- 如有架构变更，更新 `PROJECT_KNOWLEDGE_BASE.md`

## 测试要求

每次代码修改后至少运行：

```powershell
$env:PYTHONPATH='.;src;C:\Users\JM042403\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'; python -m unittest discover -s tests -p "test_*.py"
```

涉及数据处理时，需要覆盖：

- 正常值。
- 空文件。
- 缺字段。
- 空值。
- 重复数据。
- 异常金额。
- 日期范围不完整。
- 品牌归属不匹配。

涉及 API 或权限时，需要覆盖：

- 未登录。
- 无权限。
- 有权限。
- 越权访问。
- 任务归属校验。

## 第一条执行指令

从第一阶段开始。

请先不要修改代码。

只生成：

`PROJECT_REVIEW.md`

并在文档中完成：

1. 当前系统架构分析。
2. 当前技术债。
3. Ubuntu + Docker + 20+ 用户并发部署风险分析。
4. 后续阶段改造建议和优先级。

完成后等待确认，再进入第二阶段。
