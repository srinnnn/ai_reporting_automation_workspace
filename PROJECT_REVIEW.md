# PROJECT_REVIEW

审查日期：2026-07-30
当前阶段：阶段1 - 项目架构审查
审查范围：只分析，不修改代码、不移动文件、不改变运行方式。
目标环境：Ubuntu + Docker + 20+ 用户并发访问。

## 1. 当前项目目录结构

当前项目是一个以 `intranet_app` 为核心的本地内网 Web 工作台，配套浏览器插件、命令行工具、测试代码和业务资料模板。

```text
ai_reporting_automation_workspace/
├── intranet_app/                  # 本地内网工作台主程序
│   ├── app.py                     # HTTP 路由、页面渲染、业务编排主入口
│   ├── storage.py                 # SQLite 存储层和基础数据表写入/读取
│   ├── auth.py                    # 密码哈希、登录校验、session token
│   ├── ai_gateway.py              # 百炼 API 配置、调用和错误处理
│   ├── data_foundation.py         # 文件识别、字段映射、清洗、校验、入库计划
│   ├── content_pipeline.py        # P2 内容生产流水线
│   ├── archive_intake.py          # 业务资料归档和索引
│   ├── roadmap.py                 # 开发排期和能力状态数据
│   ├── scenarios.py               # P1/P2/P3 业务场景注册
│   ├── processors/                # 具体业务处理器
│   ├── samples/                   # 脱敏样例数据
│   ├── static/style.css           # 页面样式
│   └── runtime/                   # 本地数据库、上传、结果、日志，已被 Git 忽略
├── browser_extensions/            # 美团下载助手浏览器插件
├── tools/                         # 批处理、同步、批量生成、检查工具
├── tests/                         # 单元测试和页面/流程测试
├── ai_report_config_materials/    # 业务资料包；模板/说明可进 Git，真实业务数据被忽略
├── data/                          # examples/templates/local 目录规范
├── README.md
├── PROJECT_STATUS.md
├── PROJECT_KNOWLEDGE_BASE.md
├── MASTER_PROMPT.md
└── .gitignore
```

核心文件规模：

| 文件 | 行数 | 判断 |
|---|---:|---|
| `intranet_app/app.py` | 约 4755 | 职责过重，是最大维护风险 |
| `intranet_app/storage.py` | 约 1933 | 数据库 schema、迁移、Repository 混在一起 |
| `intranet_app/archive_intake.py` | 约 668 | 归档逻辑较重，后续应服务化 |
| `intranet_app/data_foundation.py` | 约 425 | 基础数据层规则相对独立，可优先保留 |
| `intranet_app/content_pipeline.py` | 约 350 | P2 流水线相对清晰，但需要异步化 |
| `intranet_app/processors/anta_meituan_reporting.py` | 约 580 | P1 美团报表核心逻辑，需保持稳定 |

## 2. 当前系统架构分析

### 2.1 前端/后端结构

当前前端不是独立前端项目，而是由 `intranet_app/app.py` 直接拼接 HTML 字符串生成页面。

当前后端使用 Python 标准库：

- `ThreadingHTTPServer`
- `BaseHTTPRequestHandler`
- 手写 GET/POST 路由分发
- 手写 HTML 页面渲染
- 手写 multipart/form-data 解析
- 手写文件下载响应

优点：

- 本地运行依赖少。
- 方便快速验证业务流程。
- 对个人工具和单机试运行足够直接。

问题：

- 没有标准 Web 框架的中间件、路由、请求校验、异常处理、权限装饰器能力。
- 页面、路由、业务逻辑、文件处理和服务编排集中在 `app.py`。
- 未来 20+ 用户同时使用时，难以做统一鉴权、日志追踪、限流、异步任务和 API 化。

### 2.2 核心模块职责

#### `intranet_app/app.py`

当前职责：

- 启动 `ThreadingHTTPServer`。
- 定义所有 GET/POST 路由。
- 登录页、首页、P1-P4 页面、数据入库页、P2 页面、自动化页、项目阶段页、AI 配置页等页面渲染。
- 读取上传文件。
- 调用 processors。
- 调用 `storage.py` 写入任务、反馈、基础层数据和结果记录。
- 调用美团插件同步逻辑。
- 调用 AI 网关。

判断：

`app.py` 已经明显超过 Controller 层职责。它同时承担 Controller、View、Service、部分 Repository 编排和文件处理职责，是当前架构升级的第一大技术债。

#### `intranet_app/storage.py`

当前职责：

- 初始化 SQLite 数据库。
- 创建用户、session、jobs、project_feedback、automation_tasks、automation_runs 等业务表。
- 创建基础数据层表：`fact_order_product`、`fact_store_finance`、`fact_store_traffic`、`fact_service_review`、`dim_product`、`dim_store` 等。
- 执行 schema 兼容升级。
- 保存任务、反馈、自动化记录。
- 保存数据入库校验结果和基础事实表。
- 读取美团基础层数据。

判断：

`storage.py` 是单文件 Repository + migration + schema bootstrap 的混合体。当前适合本地 SQLite，但不适合 PostgreSQL、多用户并发、分权限查询和可维护扩展。

#### `intranet_app/auth.py`

当前职责：

- PBKDF2 哈希密码。
- 校验密码。
- 生成 session token。

判断：

认证基础实现较好，使用 `hashlib.pbkdf2_hmac` 和 `hmac.compare_digest`，但系统级权限模型不足。当前只有轻量用户角色字段，没有完整 RBAC、资源级权限、会话过期、CSRF、防暴力登录、审计日志等企业平台能力。

#### `intranet_app/ai_gateway.py`

当前职责：

- 从环境变量或 Windows 用户环境读取百炼 API Key。
- 保存百炼 API Key 到 Windows 用户环境。
- 调用百炼兼容 OpenAI 的接口。
- 处理 HTTP 403、网络异常、超时、空响应和格式错误。

判断：

AI 调用封装已经独立出来，这是好的方向。但目前调用是同步阻塞的，并且 API Key 保存逻辑偏 Windows 本地桌面环境；云部署需要改成服务端环境变量、密钥管理或加密配置表。

#### `intranet_app/data_foundation.py`

当前职责：

- 文件类型识别。
- 平台字段映射。
- 标准字段清洗。
- 必填字段校验。
- 金额、整数、日期等格式校验。
- 品牌归属评分。
- 生成 `IngestionPlan`。

判断：

该模块职责相对清晰，是当前系统中最接近 Service/Domain 设计的部分。它体现了统一基础数据层规则，后续应保留核心算法，外层改造为 `DataFoundationService`。

#### `intranet_app/processors/`

当前职责：

- `bosch_sms.py`：博西短彩信数据处理。
- `anta_meituan_reporting.py`：安踏美团日报/周报。
- `anta_reporting.py`：安踏周报/月报历史素材处理。
- `ai_selection.py`：AI 选品辅助。
- `copy_content.py`：文案内容辅助。
- `anta_listing.py`：安踏上下架筛选。
- `anta_blacklist.py`：安踏黑名单筛选。

判断：

processors 中不少逻辑是纯函数式处理，便于测试和迁移。短期应保持不动，优先在外层增加 Service 和异步任务包装，避免直接重写业务口径。

## 3. 当前数据流分析

### 3.1 标准数据流

当前系统已经形成了正确方向：原始文件不能直接生成正式 P1/P2 结果，必须先进入基础数据层。

```text
原始 Excel/CSV
        ↓
人工上传 / 浏览器插件同步
        ↓
intake / upload 暂存区
        ↓
文件识别：平台、品牌、渠道、文件类型、日期范围
        ↓
字段映射：平台字段 → 统一字段
        ↓
数据清洗：空值、重复、金额、日期、订单状态、口径转换
        ↓
品牌归属校验
        ↓
统一基础数据层
        ├─ fact_order_product
        ├─ fact_store_finance
        ├─ fact_store_traffic
        └─ fact_service_review
        ↓
日报 / 周报 / AI 选品 / P2 内容生产
        ↓
结果 CSV / 页面预览 / 业务交付
```

### 3.2 原始 Excel/CSV 到 intake

来源包括：

- 业务人员手工导出后上传。
- 美团浏览器插件辅助下载或同步。
- 历史业务资料包中的模板和样例。

当前问题：

- 上传处理在 `app.py` 中一次性读取完整请求体，缺少文件大小限制、流式处理、病毒扫描和文件类型白名单加固。
- runtime 目录为本地文件系统路径，云部署时需要 volume 和对象存储策略。
- 插件依赖用户本地浏览器登录态，不能作为云端完全自动化抓取能力。

### 3.3 intake 到数据基础层

核心由 `data_foundation.py` 和 `storage.py` 完成。

当前优点：

- 有文件识别、字段映射、品牌归属判断。
- 有基础事实表和维度表雏形。
- 有校验失败闭环，不应直接生成正式结果。
- 金额处理倾向使用 `Decimal`。

当前问题：

- 基础表字段大量使用 `TEXT`，查询性能和类型约束不足。
- SQLite schema 和写入逻辑绑定在单个 `storage.py` 中。
- 缺少跨品牌、跨渠道、跨平台统一 ID 体系。
- 缺少批次状态机，例如 uploaded、recognized、validated、imported、failed。

### 3.4 基础层到日报/周报

安踏美团日报/周报当前通过 `load_meituan_foundation_rows()` 从基础层读取数据，再由 `anta_meituan_reporting.py` 生成结果。

当前优点：

- 符合“正式报表必须读取基础数据层”的核心规则。
- 日报支持选择日期。
- 周报支持 TOP 门店、TOP 商品和下周选品方向。
- 缺字段或无数据时会抛出 `ValidationError`。

当前问题：

- 报表生成仍在 Web 请求线程内执行。
- 结果主要为 CSV，页面化预览和版本管理还不完整。
- 多渠道日报/周报尚未统一，当前美团链路最成熟。

### 3.5 基础层到 AI 输出

P2 内容生产通过 `content_pipeline.py` 从基础层读取商品订单和评价数据，构造 AI Prompt，再通过 `ai_gateway.py` 调用百炼。

当前优点：

- 未配置 API Key 时不会伪造 AI 结果。
- AI 返回要求 JSON，缺少字段会失败。
- 有禁用词和质检提示。

当前问题：

- AI 调用同步阻塞，超时会占用 Web 请求线程。
- AI 任务没有后台队列、重试、取消、限流和成本统计。
- 品牌知识库、商品信息库、活动日历尚未完整接入。
- AI 输出版本、审核、驳回和复用机制不足。

## 4. 当前技术债

### 4.1 `app.py` 职责过重

结论：严重。

证据：

- `app.py` 约 4755 行。
- 同时承担路由、HTML、表单解析、文件上传、业务编排、AI 调用、插件同步、数据查询和结果下载。
- GET/POST 路由用大量 `if path == ...` 和 `if path.startswith(...)` 手工分发。

风险：

- 新功能继续加入会显著增加回归风险。
- 权限、异常、日志、响应格式难以统一。
- 难以拆成云端 API、worker 和前端页面。

建议：

先不要重写业务逻辑。下一阶段应先建立 `backend/services` 和 `backend/repositories` 外壳，把数据入库、P1 报表、P2 内容生产逐步迁移出 `app.py`。

### 4.2 模块耦合问题

结论：中高风险。

现状：

- `app.py` 直接依赖 `storage.py`、`data_foundation.py`、`content_pipeline.py`、processors、工具脚本路径和模板路径。
- `storage.py` 同时知道 schema、业务表、基础层表、数据转换和加载方法。
- processors 相对独立，但被 `app.py` 直接调用。

风险：

- 迁移 PostgreSQL 时会影响大量调用点。
- 增加新渠道时容易复制已有流程，而不是沉淀统一抽象。
- 权限隔离难以后置补丁式加入。

建议：

新增 Service 层承接业务编排，Repository 层统一数据库读写，逐步让 `app.py` 只负责请求响应。

### 4.3 数据库设计问题

结论：当前适合本地试运行，不适合生产并发。

现状：

- 使用 SQLite 文件：`intranet_app/runtime/intranet.sqlite3`。
- 每次操作新建连接，写入时直接 commit。
- 基础事实表字段大量为 `TEXT`。
- 缺少 RBAC 表、资源授权表、操作审计表。
- 缺少数据库迁移工具，例如 Alembic。

风险：

- 20+ 用户同时上传、生成、写入时 SQLite 写锁会成为瓶颈。
- 缺少连接池和事务边界管理。
- 报表查询随数据增长会变慢。
- 难以支持品牌/渠道/项目级隔离。

建议：

第三阶段迁移 PostgreSQL，但迁移前先抽象 Repository，避免一次性大改。

### 4.4 并发风险

结论：中高风险。

现状：

- Web Server 是 `ThreadingHTTPServer`，可以多线程处理请求。
- Excel 上传、文件解析、报表生成、AI 调用都在请求线程内同步执行。
- SQLite 对并发写入支持有限。
- 文件写入 runtime/result/upload 目录，缺少统一锁、任务状态机和重复提交防护。

风险：

- 5 人同时上传大 Excel 可能造成内存高峰。
- 2 人同时调用 AI 会占用请求线程直到外部接口返回。
- 多个任务同时写 SQLite 容易出现 database locked。
- 报表生成超时后用户无法明确知道任务是否仍在后台执行。

建议：

引入 Redis + Celery，把上传解析、入库、报表生成、AI 生成转为异步任务。

### 4.5 安全风险

结论：生产前必须整改。

现状优点：

- 密码哈希使用 PBKDF2。
- session token 使用安全随机数。
- 默认 `.gitignore` 已保护真实业务数据、runtime、SQLite、Excel/CSV。
- 局域网模式下对默认密码有校验意图。

主要风险：

- 无完整 RBAC 权限模型。
- session 缺少过期机制和服务端清理策略。
- 缺少 CSRF 防护。
- 文件上传缺少大小限制、扩展名白名单、内容类型校验和恶意文件检测。
- API Key 当前偏 Windows 用户环境存储，不适合云端统一管理。
- 操作审计不足。
- 浏览器插件权限和后台导出能力需要最小权限审查。

建议：

第五阶段建立 RBAC，并在第二阶段拆分 API 时同步引入统一鉴权和权限检查。

### 4.6 部署风险

结论：当前不能直接作为云端生产服务部署。

现状：

- 无 Dockerfile。
- 无 docker-compose.yml。
- 无 nginx 配置。
- 无 PostgreSQL/Redis 配置。
- 无健康检查。
- 无生产日志规范。
- 无进程管理和 worker。
- 配置中存在本地默认路径和 Windows API Key 保存逻辑。

建议：

第六阶段补齐 Docker Compose，服务包含 backend、worker、postgres、redis、nginx。

## 5. 云部署风险分析：Ubuntu + Docker + 20 用户并发

### 5.1 当前是否支持

不支持直接生产部署。

当前系统可以作为本地/内网试运行工作台，但不满足企业内部 20+ 用户并发平台的生产要求。主要缺口不是某一个 bug，而是运行模型、数据库、任务系统、权限系统和部署方式都仍是单机工具形态。

### 5.2 当前最大瓶颈

第一瓶颈：同步请求线程承担重任务。

- Excel 上传和解析同步执行。
- 报表生成同步执行。
- AI 调用同步执行。
- 用户等待期间请求线程被占用。

第二瓶颈：SQLite 并发写入。

- 20+ 用户同时写任务、上传、入库、生成结果时容易出现写锁争用。
- 缺少连接池和事务管理。

第三瓶颈：`app.py` 单体化。

- 所有业务都堆在一个文件中，后续加入权限、异步、API 化会变得高风险。

第四瓶颈：权限和数据隔离不足。

- 目前无法稳定表达“某用户只能看某品牌/某渠道/某项目”。

### 5.3 必须修改模块

必须修改或抽象的模块：

- `intranet_app/app.py`：拆出 Controller/API、Service、页面渲染和任务提交逻辑。
- `intranet_app/storage.py`：抽象 Repository，准备 PostgreSQL 迁移。
- `intranet_app/ai_gateway.py`：改为云端环境变量/密钥管理，AI 调用进入异步任务。
- `intranet_app/data_foundation.py`：保留核心规则，但由 Service 包装为可复用入库流程。
- 报表入口：从同步生成改为提交任务、查询任务状态、下载结果。
- 文件上传入口：增加大小限制、文件校验、异步处理和对象/volume 存储策略。
- 认证授权：从简单 role 字段升级为 RBAC。

### 5.4 可以暂时保留模块

可以暂时保留但需要外层包装的模块：

- `processors/anta_meituan_reporting.py`：业务口径成熟，短期不要重写。
- `processors/bosch_sms.py`：短彩信处理逻辑可保留。
- `processors/anta_listing.py`、`processors/anta_blacklist.py`：配置筛选逻辑可保留。
- `data_foundation.py` 的字段识别、清洗、校验算法可保留。
- `content_pipeline.py` 的 P2 候选商品和 Prompt 组装逻辑可保留。
- `browser_extensions/` 可作为半自动导出工具继续保留，但不能视为云端自动抓取能力。
- `tests/` 现有测试可保留，并在每次迁移时扩展。

## 6. 建议目标改造路径

### 阶段 2：后端分层，不改业务口径

优先建立：

```text
backend/
├── api/
├── services/
├── repositories/
├── models/
├── schemas/
├── core/
├── workers/
└── main.py
```

建议从低风险开始：

1. 抽 `DataFoundationService`，包装现有 `build_ingestion_plan()` 和 `storage.save_foundation_fact_rows()`。
2. 抽 `ReportService`，包装安踏美团日报/周报生成。
3. 抽 `AiContentService`，包装 P2 内容生产。
4. 抽 `AiService`，包装 `BailianClient`。
5. 抽 Repository 接口，先由 SQLite 实现，再准备 PostgreSQL 实现。

### 阶段 3：数据库升级到 PostgreSQL

优先设计表：

- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `brands`
- `channels`
- `platforms`
- `projects`
- `project_members`
- `source_files`
- `data_import_batches`
- `field_mapping_rules`
- `validation_reports`
- `products`
- `stores`
- `sales_fact`
- `finance_fact`
- `traffic_fact`
- `service_review_fact`
- `reports`
- `report_versions`
- `ai_tasks`
- `ai_outputs`

迁移原则：

- 先新增 Repository 抽象。
- 再设计 PostgreSQL schema。
- 最后替换 SQLite 实现。
- 迁移期间保留 SQLite 本地试运行能力。

### 阶段 4：异步任务系统

引入 Redis + Celery。

优先异步化：

1. Excel/CSV 上传识别。
2. 数据清洗入库。
3. 日报/周报/月报生成。
4. P2 AI 内容生成。
5. 插件同步后的自动入库。

### 阶段 5：RBAC 权限系统

角色建议：

- 管理员：全局管理。
- 业务负责人：负责品牌/项目管理。
- 小组长：负责范围内审核和查看。
- 普通用户：上传、生成、查看自己的结果。

必须实现：

- 登录态校验。
- 品牌/渠道/项目数据权限。
- 后台任务权限继承。
- 操作审计。

### 阶段 6：Docker 云部署

目标服务：

```text
nginx
backend
worker
postgres
redis
```

必须新增：

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `nginx.conf`
- 健康检查接口
- 部署说明

### 阶段 7：性能测试

测试设计：

- 10 人浏览。
- 5 人上传 Excel。
- 3 人生成日报。
- 2 人调用 AI。

指标：

- CPU。
- Memory。
- Response Time。
- Error Rate。
- Queue Length。
- DB Connections。
- Worker Duration。

输出：`PERFORMANCE_TEST.md`。

## 7. 第一阶段结论

当前项目已经具备清晰业务价值和可验证的本地 MVP：

- P1/P2 的基础业务链路已形成。
- 数据基础层规则方向正确。
- 安踏美团日报/周报和 P2 内容生产已有可运行基础。
- Git 上传边界已经做了初步保护。

但当前系统仍是“本地个人/小组试运行工具”，还不是“企业内部 20+ 用户生产平台”。

升级优先级建议：

1. 先拆 `app.py`，建立 Service/Repository 边界。
2. 再引入异步任务，解决 Excel/AI/报表阻塞问题。
3. 再迁移 PostgreSQL，解决并发和历史数据治理问题。
4. 同步补 RBAC 和审计，解决企业内部使用的安全边界。
5. 最后做 Docker Compose 和性能测试，进入可部署 MVP。

第一阶段已完成审查。下一步应在确认后进入第二阶段：后端架构优化方案设计，不建议直接大规模改代码。
