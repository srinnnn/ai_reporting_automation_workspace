# RPT-001 Engineering Baseline

> Reporting Automation 工程基线审核报告(AUDIT TASK)
>
> - 执行方:DeepSeek / Reasonix
> - 审核范围:仅工程基线审计,不修改业务代码、不做重构
> - Audit Baseline:`a25ef13150d5f3554fe0f19277c62f71dbc4cc5c`
> - Repository Visibility:**PUBLIC**(任务已知输入条件)
> - 审核环境:独立 Audit Worktree(隔离自原工作区 FROZEN_LOCAL_WIP)

---

## 1. Executive Summary

Reporting Automation 是一个**功能完整但处于治理过渡期**的工程:242 个 tracked 文件、约 2.4 万行源码,实现了"美团下载插件 → intake → foundation → 正式报告/P2 内容"的完整链路,并有 49 个测试文件的测试套件(265 个用例)。

总体结论:

- **数据边界大体建立但未全覆盖**:美团日报/周报(web + task 模式)与 P2 内容生产中心已走 intake → foundation(fact_* 表)且 fail-closed;但**安踏周报/月报初稿仍直接读取 `01_raw_data` 原始文件生成正式 P1 输出**,另有 `/scenario/*/run` 与安踏黑名单入口允许上传 raw 文件直接驱动 P1/P2 处理器——违反 AGENTS.md Mandatory Data Path。
- **Git / 安全状态良好**:当前 HEAD 与全部 git history(6 commits)未发现真实敏感数据;tracked 的 31 个 xlsx 全为 template、8 个 csv 全为 samples;`.env` 不存在;代码无 secret 形态。Repository 为 PUBLIC 但无已证实的数据泄露,列为 governance finding(建议转 Private),不构成 P0。
- **架构处于双代过渡**:6004 行的 `app.py` 上帝模块是运行时主体;backend 新层(container/service/repository)已 wiring 且被 console/task API 使用,但 SQLite repository 只是 legacy AppStorage 的转发器;PostgreSQL 为纯 skeleton。任务系统为 feature-flag 灰度(默认 legacy)。
- **测试基线不可信**:隔离环境安全执行 265 个用例,259 PASS / 5 FAIL + 1 ERROR(3 个依赖缺失的本地规划排期 xlsx,3 个 task-detail 页面断言与代码文案不同步)。测试本身隔离良好(临时 DB / mock / tempfile),无真实业务环境访问。

Issue 评级:**P0 = 0, P1 = 2, P2 = 9, P3 = 7**(独立 Issue 18 项,可由 §15 精确反算)。

## 2. Audit Baseline

| 项目 | 值 |
|---|---|
| Repository | `srinnnn/ai_reporting_automation_workspace` |
| Visibility | PUBLIC |
| Audit Baseline | `a25ef13150d5f3554fe0f19277c62f71dbc4cc5c` |
| Audit Branch | `chore/rpt-001-engineering-baseline` |
| Audit Worktree | `C:\Users\JM042403\Documents\ai_reporting_automation_workspace_rpt001` |
| 原工作区 | FROZEN_LOCAL_WIP(main, 12 modified + 7 untracked, 未纳入本审计) |
| Worktree 状态 | clean |

## 3. Repository Inventory

### 3.1 资产统计

| 类别 | 数量 |
|---|---|
| tracked 文件总数 | 242 |
| Python 文件 | 121 |
| 文档(.md) | 46 |
| Excel(.xlsx) | 31(全部为 `*_template.xlsx` / `*_example.xlsx`) |
| CSV | 8(全部为 `intranet_app/samples/*_sample.csv`) |
| 启动脚本(.bat) | 9 |
| JSON | 7 |
| JS / MJS | 3 / 3(浏览器插件 + 工具) |
| Docker 相关 | Dockerfile、docker-compose.yml、.dockerignore |
| 数据库相关 | database/postgresql/{schema.sql, README.md} |
| CSS | 1 |
| 测试文件 | 49(测试用例 265 个) |

### 3.2 主要目录

```
ai_reporting_automation_workspace_rpt001/
├── intranet_app/            # 运行主体(约 35 文件)
│   ├── app.py               # 6004 行(路由+页面+业务+编排)
│   ├── storage.py           # 2009 行(SQLite DAO)
│   ├── archive_intake.py    # 668 行
│   ├── data_foundation.py   # 425 行(识别/映射/清洗/校验,纯逻辑)
│   ├── processors/          # anta_meituan_reporting(580)/ai_selection(252)/anta_reporting(189)/copy_content(137)/bosch_sms(99)
│   ├── content_pipeline.py  # 350 行(P2 内容)
│   ├── ai_gateway.py        # 195 行(Bailian)
│   ├── config.py / auth.py / domain.py / io_utils.py ...
│   ├── static/ runtime/(ignored) samples/(8 csv)
│   └── anta_retail_launcher.py  # 含硬编码绝对路径
├── backend/                 # 44 文件(container/services/repositories/adapters/workers)
│   ├── core/                # config.py / container.py
│   ├── services/            # report_service / ai_service / task_service ...
│   ├── repositories/        # sqlite/ + postgresql/(skeleton)
│   ├── adapters/            # report_task_adapter ...
│   └── workers/executors/   # report_executor ...
├── browser_extensions/meituan_download_assistant/  # 美团下载插件(8 文件)
├── tools/                   # 8 文件(同步/生成/检查工具)
├── tests/                   # 49 文件
├── ai_report_config_materials/  # 42 文件(模板 xlsx + 文档)
├── data/                    # examples/templates(入库), local/(ignored)
├── database/postgresql/     # schema.sql + README(设计骨架)
├── docs/                    # 11 文件(迁移计划/RBAC 设计等)
└── *.bat 启动脚本 + AGENTS.md + README + PROJECT_STATUS + 迁移规划文档
```

### 3.3 代码规模(Top 文件)

| 文件 | LOC | 职责 |
|---|---|---|
| `intranet_app/app.py` | 6004 | 路由 + HTML 渲染 + 业务 + 编排(上帝模块) |
| `intranet_app/storage.py` | 2009 | SQLite DAO(用户/会话/任务/反馈/效率/事实表) |
| `intranet_app/archive_intake.py` | 668 | 投递资料 intake |
| `intranet_app/processors/anta_meituan_reporting.py` | 580 | 美团日报/周报计算(纯函数) |
| `intranet_app/data_foundation.py` | 425 | foundation 识别/映射/清洗/校验(纯逻辑) |
| `intranet_app/content_pipeline.py` | 350 | P2 内容组装(纯内存) |
| `intranet_app/roadmap.py` | 311 | 开发路线 |
| `intranet_app/processors/ai_selection.py` | 252 | AI 选品(纯函数) |
| `intranet_app/ai_gateway.py` | 195 | Bailian 网关 |

## 4. Architecture

### 4.1 分层确认(以代码为准)

```
美团插件 / 上传 / Downloads 同步
    ↓ intake(允许读取 raw)
data_foundation.py(识别/映射/清洗/校验,纯逻辑)
    ↓ save_foundation_fact_rows → fact_* 表(SQLite)
P1(美团日报/周报, web+task)/ P2(内容中心)
    ↓ load_meituan_foundation_rows(fail-closed)
正式输出(CSV / 内容包)
```

### 4.2 运行时主体

- **`intranet_app/app.py`(6004 行)**:`IntranetApp` 类承担全部职责——`handle_get`(436-568,约 30 个分支)/`handle_post`(570-649,约 25 个分支)路由、约 60 个内联 f-string HTML 渲染函数(约 55-58% 行数)、业务 handler、任务编排、container wiring。**无模板引擎、无分层**(ISSUE-02)。
- **`intranet_app/storage.py`(2009 行)**:`AppStorage` monolithic SQLite DAO,同时管理用户/会话/任务/反馈/效率映射/foundation 事实表 6 大领域,内联大量 DDL(归入 ISSUE-02 架构类)。

### 4.3 backend 新层现状

- `backend/core/container.py` 启动即构建 container;console/task API 走 container 服务。
- 但 `backend/repositories/sqlite/*` 只是 **AppStorage 的转发器**(真 wiring、假分层):数据模型仍是 legacy 表/记录。
- 双套 DI 装配重复:`app.py:1208-1230`(`_task_submitter` fallback)与 `container.py:178-221`(`_build_service_bundle`/`_build_worker_bundle`)装配同一套对象图(ISSUE-07)。
- `database/postgresql/schema.sql` + README 为**纯设计产物**,README 自述 "design artifact only";`backend/repositories/postgresql/*` 写方法全部 `raise NotImplementedError`,仅被 `tests/test_postgresql_task_repository.py` 引用 = dead code(ISSUE-13)。
- 任务系统:`TaskSubmitter/TaskRunner` 真实实现但仅覆盖美团日报一景;`REPORT_TASK_MODE=task` 才启用,默认 `legacy`;automation 模块(自动化任务/执行记录)与任务系统互不相通(ISSUE-18)。

### 4.4 分层合规性

- ✅ 美团日报/周报(web 模式):`app.py:1037-1041` sync → ingest → `_load_anta_meituan_sources_from_foundation`,fail-closed(`storage.py:1633-1655` 仅查 fact_* 表)。
- ✅ 美团日报(task 模式):`source_policy="foundation_only"`(backend/adapters/report_task_adapter.py:20-47),executor → ReportService 仅 `query_foundation_rows`。
- ✅ P2 内容中心:`app.py:1266-1317` sync+ingest → `load_meituan_foundation_rows` → `build_p2_content_pack`。
- ❌ **安踏周报/月报**:route `/anta-reporting/weekly/run`、`/monthly/run`(app.py:622-627)→ `_handle_anta_reporting_run`(993-1023)→ `_build_anta_weekly/monthly_report`(1571-1596)**直接 `read_table` 读取 `01_raw_data`**(ISSUE-01)。

## 5. Code Quality

- **ISSUE-02 (P2)** `app.py` 上帝模块:6004 行混合路由/HTML/业务/编排;单函数超 100 行者众(`_automation_runs_page` 159 行、`_development_roadmap_page` 118 行等)。
- **ISSUE-07 (P2)** 双套 DI 装配重复 + SQLite repository 假分层(见 §4.3)。
- **ISSUE-15 (P3)** 重复代码:`_group_development_tree_panel` 同名定义两次(app.py:2006-2054 被 2205-2236 覆盖,旧版成死代码);multipart 解析近重复 3 次(`_read_multipart`/`_read_multipart_files`/`_read_file_list`);`_format_efficiency_gain` 与 `_format_time_saved` 结构几乎相同。
- **ISSUE-12 (P3)** 死代码:`_load_anta_meituan_sources` 全家(app.py:1598-1636、1721-1743、1745-1782,含 Downloads/runtime/intake/01_raw_data fallback)**全仓库无生产调用者**,生产路径用 `_load_anta_meituan_sources_from_foundation`;一旦重新接线即直接违反 AGENTS.md。

## 6. Data Boundary(本项目最高优先级)

### 6.1 Mandatory Data Path 验证

| 输出路径 | 数据来源 | 判定 |
|---|---|---|
| 美团日报(web) | sync→ingest→fact_* | ✅ 合规 |
| 美团日报(task 模式) | foundation_only | ✅ 合规 |
| 美团周报(web) | ingest→fact_* | ✅ 合规 |
| P2 内容中心 | ingest→fact_* | ✅ 合规 |
| **安踏周报初稿** | `01_raw_data` 直接 read_table | ❌ **ISSUE-01** |
| **安踏月报初稿** | `01_raw_data` 直接 read_table | ❌ **ISSUE-01** |
| `/scenario/*/run`(AI 选品/文案) | 用户上传 raw 直驱 processor | ⚠️ **ISSUE-04** |
| 安踏黑名单 | 上传 4 个 raw 文件直驱 | ⚠️ **ISSUE-05** |

### 6.2 ISSUE-01 — 安踏周报/月报正式 P1 报告直接读 raw(P1)

- 证据:`app.py:622-627` route → `_handle_anta_reporting_run`(993-1023)→ `_build_anta_weekly_report`(1571-1581)/`_build_anta_monthly_report`(1583-1596)直接 `read_table` 读取 `01_data_processing/01-3_weekly_report/anta_weekly_report/01_raw_data` 与 `01-4_monthly_report/.../01_raw_data`。
- 页面文案佐证:`app.py:4959-4967` "读取安踏周报原始数据目录中的最新美团、京东数据"。
- backend 侧佐证未迁移:`backend/services/report_service.py:105` `raise NotImplementedError("Meituan monthly report is not foundation-backed yet")`。
- 违反 `AGENTS.md:51/63/65`(正式 P1 必须读 foundation、fail-closed、raw 只作 intake)。
- 建议方向:对齐美团模式(sync→ingest→fact_* 读取);`read_table` 读取 raw 仅保留给 intake/迁移工具。

### 6.3 ISSUE-04 — /scenario 上传 raw 直驱 P2 处理器(P2)

- 证据:`app.py:585-588` route `/scenario/*/run` → `app.py:965` `read_table(uploaded_file...)` → `app.py:969-970` `PROCESSORS[scenario_key](rows)` 直接产出正式输出并 save_job;PROCESSORS 注册(app.py:97-101)含 `ai_selection.process`(AI 选品)、`copy_content.process`(文案)。
- 违反 AGENTS.md:63(上传 raw 不得直接用于正式输出)。processors 为纯函数,风险低于 ISSUE-01,但仍是 raw→正式 P2 直连。

### 6.4 ISSUE-05 — 安踏黑名单上传 raw 直驱 P1(P2)

- 证据:`_handle_anta_blacklist_run`(`app.py:1492-1532`)要求上传 4 个 raw 文件直接生成 P1 黑名单输出。

### 6.5 合规点确认

- foundation 读取 fail-closed:`storage.py:1633-1655` `load_meituan_foundation_rows` 与 1864-1989 各 `_load_meituan_*_rows` 仅 `SELECT * FROM fact_* WHERE brand_id/platform/channel`,无 raw 回退。
- `data_foundation.py` 为纯逻辑(无文件 I/O);ingest 读取发生在 app.py handler(上传/插件 intake,允许)。
- Downloads 扫描仅发生在 intake 阶段(`app.py:1445-1452` `_meituan_download_sync_configs`,合规)。
- **ISSUE-16 (P3)** dashboard 非正式输出读真实桌面/下载 Excel:`app.py:93` `CHANNEL_BRAND_DISTRIBUTION_PATH = Path.home()/Desktop/工作文件/西门子/短信数据/5.30数据done/平台-品牌-渠道分布.xlsx`、`app.py:2870` `Path.home()/Downloads/内容任务耗时统计.xlsx`,仅首页展示用,缺失返回空(fail-open 但不影响输出)。

## 7. Excel / CSV / Template Governance

### 7.1 tracked 文件性质

- **31 个 xlsx 全部为 `*_template.xlsx` / `*_example.xlsx`**(位于 `ai_report_config_materials/` 与 `data/templates/`),大小 12-13KB。
- **8 个 csv 全部为 `intranet_app/samples/*_sample.csv`**,大小 225-419 字节。
- 未发现文件名像数据而实际是数据的 tracked 文件。

### 7.1b 结构级扫描(REWORK 补充)

- **XLSX(31 个)结构扫描完成**:每文件 sheet 数 5(例外 `copy_content_template_anta_kids_example.xlsx` 为 3),非空单元格计数 ≤ 191/文件(read_only 上限内),**无任何文件出现大量数据行**;全部符合模板特征(header + 少量示例占位 + 空行)。suspicious_files: **none**。
- **CSV(8 个)结构扫描完成**:全部 header=yes、data_rows ≤ 3、cols 7-12,确认为 **small synthetic sample**。
- 未打印任何单元格/文件内容值(仅统计行/列/非空计数)。

### 7.2 .gitignore 兜底(评价:良好)

- `*.csv/*.xls/*.xlsx/*.docx/*.pptx/*.zip` 等默认 deny(第 58-83 行)。
- `ai_report_config_materials/**/01_raw_data/`、`02_manual_deliverables/`、`03_unresolved/`、`meituan_auto_download/`、`jd_export/`、`tmall_export/` 等业务敏感目录明确保护。
- 模板白名单例外(`*template*.xlsx` 等)后**重新应用敏感目录保护**(第 149-157 行),顺序正确。
- `data/local/**` ignore、`intranet_app/runtime/` ignore。

## 8. Git / GitHub Security(Public Repository 专项)

### 8.1 检查结论

| 检查项 | 结果 |
|---|---|
| Current HEAD tracked 敏感内容 | **No confirmed sensitive data found within audit scope**(无 .env/.db/session/token/password 文件形态;代码 secret 形态 grep 零命中) |
| Git history 敏感路径 | **未发现**(6 commits `git log --all --name-only` 对 .env/.db/session/cookie/token/secret/password/runtime/outputs/uploads/raw/manual 等零命中) |
| Git history 内容级 Secret 扫描 | **完成**(6 commits × 关键词 api_key/secret/token/password/cookie/session/bearer/access_key 等 + 赋值形态扫描):48 个赋值命中**全部为 tests/ TEST_FIXTURE**(`default_admin_password`/`api_key` 的 fake 值),无生产代码硬编码密钥 |
| 本地 .env | 不存在 |
| Repository visibility | PUBLIC |
| P0 blocker | **无**(无 CONFIRMED_REAL_SECRET / POTENTIAL_REAL_SECRET,不设 P0) |

> 安全结论措辞:审计范围内**未发现已确认的敏感数据**("No confirmed sensitive data found within audit scope.");以上为完整验证结果而非仅"无证据"。

### 8.2 ISSUE-11 (P2) — Public Repository Governance

- 该仓库是**组内业务中台**(含品牌/渠道/项目/效率数据模型与真实业务材料目录结构),代码本身未泄露敏感数据,但 PUBLIC 与业务性质不匹配。
- 回答(§21 要求):
  1. 当前 HEAD 是否发现敏感数据?——否(仅模板/样例/代码/文档)。
  2. Git history 是否发现敏感数据?——否(6 commits 无敏感路径)。
  3. Public 是否符合业务性质?——**不符合**,建议转 Private(组内业务系统)。
  4. 是否建议转 Private?——是。
  5. 是否存在需要 history remediation 的证据?——**无**。
- 不擅自修改 visibility,由 ChatGPT/用户决定。

## 9. Configuration

### 9.1 ISSUE-03 (P1) — 双配置系统并存且行为不一致

- `backend/core/config.py:144-161` 用 `dotenv_values()` 读取 `.env` 文件;`intranet_app/config.py:40-48` 的 `DEFAULT_CONFIG` 只调 `os.environ.get`,**完全不加载 `.env`**。
- 后果:`.env` 中的 `INTRANET_SECRET_KEY`、`INTRANET_ADMIN_PASSWORD` 对 `DEFAULT_CONFIG` **无效**(除非 shell 已设同名变量);服务器 host/port/admin 密码走 `DEFAULT_CONFIG`(app.py:5957-5990),而 REPORT_TASK_MODE/DB/AI 走 `load_core_config()`。
- 另有 `app.py:1138` 把 `self.config.result_dir`(AppConfig,不读 env)塞入 task payload,与 backend 容器的 `config.files.result_dir`(读 env)非同一来源。

### 9.2 ISSUE-04b → 归入 03 的默认密钥 fail open(独立编号 ISSUE-06, P2)

- `intranet_app/config.py:43` `INTRANET_SECRET_KEY` 缺省回退 `"change-this-before-shared-intranet-use"`;`:48` `INTRANET_ADMIN_PASSWORD` 缺省 `"admin123"`。
- LAN 模式(host≠localhost)只校验 admin 密码强度,**不校验 secret key 是否仍为默认值**。

### 9.3 其他配置发现

- `SQLITE_PATH=/app/intranet_app/runtime/intranet.sqlite3`(.env.example:16)是 Docker 路径,Windows 复制模板后解析到错误位置(P3)。
- `REPORT_TASK_MODE` 非法值 = warning + silent fallback 到 legacy,非 fail-closed(backend/core/config.py:164-172;app.py:105-110 再包一层)(P3,ISSUE-17)。
- `AI_PROVIDER` 是死配置:只有 `bailian` 分支实现(backend/services/ai_service.py:71,102)(P3,ISSUE-17)。
- **ISSUE-10 (P2) 硬编码本机绝对路径**:`intranet_app/anta_retail_launcher.py:10` `DEFAULT_PROJECT_ROOT = Path(r"C:\Users\JM042403\Documents\安踏即时零售（上下架筛选+选品）")`(其他机器直接抛错);`app.py:93` Desktop 路径;`tools/*.mjs` `C:/Users/JM042403/Downloads/...`。

## 10. Exception Handling

- **ISSUE-08 (P2)** 内部异常字符串(含路径)原样回传 UI/API 且无 traceback:多处 handler 把 `str(exc)` 直接渲染进错误页/返回给前端。
- ✅ 测试可见 `ERROR:root:task executor failed ... error=RuntimeError` 等 logging 存在,说明 executor 失败有日志;但用户侧无结构化错误码。
- ✅ 未发现 silent bare except;绝大多数异常有明确类型捕获(ValidationError/ValueError/TypeError/FileNotFoundError 等)。

## 11. Logging

- ✅ 应用使用 `logging`(`application log`);容器初始化、任务执行失败、AI 生成失败均有 `INFO/ERROR` 日志。
- ✅ 未发现日志记录 Token/Cookie/API Key;`ai_gateway` 失败仅记录 provider/model/attempt。
- ⚠️ `print()` 仍存在于部分工具脚本(tools/),不影响生产路径。
- 区分:application log(`logging`)、business audit record(storage 表)、task status(任务表)、console print(测试/工具)——四类可辨识,核心业务路径有日志覆盖。

## 12. Testing

### 12.1 执行结果(隔离环境,Audit Worktree)

```text
python -m unittest discover -s tests -p "test_*.py"
Ran 265 tests in 13.039s
FAILED (failures=5, errors=1)
```

| 状态 | 数量 | 说明 |
|---|---|---|
| PASS | 259 | 全部使用 tempfile/临时 DB/mock,隔离安全 |
| FAIL | 5 | 见下 |
| ERROR | 1 | 见下 |
| SKIP | 0 | 项目无 skip 装饰器 |

### 12.2 失败清单与分析

| 用例 | 类别 | 根因 |
|---|---|---|
| `test_saved_not_improved_state_overrides_default_improved_rule`(ERROR) | 环境 | 依赖本地规划排期 xlsx(`AI自动化替代开发规划与排期_...xlsx`,Git 中不存在)→ StopIteration |
| `test_dashboard_prioritizes_priority_entry...`(FAIL) | 环境 | app.py:3348 `assert result`(xlsx 缺失返回空) |
| `test_page_and_dashboard_expose_automation_entry`(FAIL) | 环境 | 同上(经 `_dashboard` → `_group_development_tree_panel` → `_completed_feedback_items_for_dashboard`) |
| `test_failed_task_detail_shows_error_diagnostics`(FAIL) | **代码/测试不同步** | 断言 `"download available"` 未找到;页面文案为中文"任务失败,无结果文件" |
| `test_success_task_detail_shows_result_asset_status`(FAIL) | **代码/测试不同步** | 断言 `"Result Asset"` 未找到;页面为中文渲染 |
| `test_task_detail_page_shows_status_and_error`(FAIL) | **代码/测试不同步** | 断言 `"暂无可下载文件"` 未找到;页面文案为"任务失败,无结果文件" |

### 12.3 测试隔离性(评价:良好)

- 无测试访问 `data/local`、真实 SQLite(全部 tempfile)、真实 Bailian/美团/JD/Tmall 网络、真实登录 session;ai_gateway 测试 patch `urlopen` 或注入 fake client;AI 失败 WARNING 为测试内预期路径。
- 测试写入全部落在 `tempfile.TemporaryDirectory()`。
- **ISSUE-09 (P2) 测试基线不可信**:6 个 non-passing(5 FAIL + 1 ERROR)中 3 个为环境依赖(测试读取 Git 未入库的真实规划排期 xlsx,`app.py:94/2495`),3 个为 task-detail 断言与代码文案不同步——baseline 已提交状态下测试套件即非全绿,无法建立可信回归基线。

## 13. Documentation

- **ISSUE-10b (P2,并入 ISSUE-10 文档项)** `AGENTS.md:46` 测试命令含本机绝对路径 `C:\Users\JM042403\.cache\codex-runtimes\...` 且 `src` 目录不存在(历史遗留);同款路径还出现在 `CONTRIBUTING.md:60`、`MASTER_PROMPT.md:424`、`README.md:46`——其他机器/CI 直接复制命令即失败。
- **ISSUE-17b (P3,并入 ISSUE-17)** `PROJECT_KNOWLEDGE_BASE.md:4` 含乱码编码内容(旧工作区路径,编码已损坏)。
- ✅ 迁移规划文档(ARCHITECTURE_PLAN/APPLICATION_CONTAINER_MIGRATION_STATUS/POSTGRESQL_MIGRATION_PLAN 等)与代码基本一致:文档标注 skeleton 的(database/postgresql)代码确实是 skeleton。
- ⚠️ 46 个 .md 文档量大,PROJECT_STATUS/迁移文档有失去 Source of Truth 价值的趋势(非阻塞)。

## 14. Portability / Deployment

| 维度 | 现状 | 判定 |
|---|---|---|
| Windows 绝对路径 | `anta_retail_launcher.py:10`、`app.py:93/2870`、AGENTS 测试命令、tools/*.mjs | ⚠️ ISSUE-10 (P2/P3) |
| .bat 启动脚本(9 个) | 全部 `cd /d "%~dp0"` 相对自身路径 | ✅ 可移植性好 |
| Docker | Dockerfile(python:3.12-slim)、docker-compose.yml 存在,容器强制 sqlite | ✅ 存在;容器内 Path.home() 指向 /root,缺失文件时页面降级不崩溃 |
| SQLite→PostgreSQL | `backend/repositories/postgresql/*` 全 NotImplementedError;`container.py:143-144` `if backend != "sqlite": raise NotImplementedError`;requirements.txt 无 psycopg2 | ⚠️ 切换未实现(skeleton,ISSUE-13 P3) |
| 会话/数据存储 | SQLite 文件 + runtime 目录(ignored) | ✅ |
| 文件编码 | Python 源码 UTF-8;PROJECT_KNOWLEDGE_BASE.md 例外(损坏) | ⚠️ |

结论:生产代码不阻碍未来 Docker/NAS 迁移,主要阻碍为本机绝对路径硬编码与 PostgreSQL skeleton;不因未来可能迁移而建议引入 Kubernetes/Redis Cluster 等(无真实需求)。

## 15. Issue Summary

```
P0: 0
P1: 2   (ISSUE-01 安踏周报/月报 raw fallback、ISSUE-03 双配置系统)
P2: 9   (ISSUE-02 app.py 上帝模块、ISSUE-04 /scenario 上传 raw 直驱 P2、ISSUE-05 安踏黑名单 raw 直驱 P1、
        ISSUE-06 默认密钥 fail open、ISSUE-07 backend 假分层+双 DI、ISSUE-08 异常回传无 traceback、
        ISSUE-09 测试基线不可信、ISSUE-10 本机绝对路径硬编码、ISSUE-11 Public repository governance)
P3: 7   (ISSUE-12 死代码 _load_anta_meituan_sources、ISSUE-13 PostgreSQL skeleton dead code、
        ISSUE-14 dashboard 读桌面/下载 Excel、ISSUE-15 重复代码、
        ISSUE-16 配置 silent fallback/AI_PROVIDER 死配置、
        ISSUE-17 文档编码损坏/文档量大、ISSUE-18 任务系统灰度与 automation 不相通)
```

> 计数规则:独立 Issue 18 项 = P1 2 + P2 9 + P3 7,可由 §15.1 Detailed Findings 精确反算。

## 15.1 Detailed Findings

### ISSUE-01 — 安踏周报/月报正式 P1 报告直接读取 raw 数据目录(P1)
- Evidence: `intranet_app/app.py:622-627`(route `/anta-reporting/weekly/run`、`/monthly/run`)→ `_handle_anta_reporting_run`(993-1023)→ `_build_anta_weekly_report`(1571-1581)/`_build_anta_monthly_report`(1583-1596)直接 `read_table` 读取 `01_raw_data`;页面文案 `app.py:4959-4967`。
- observed behavior:正式 P1 周报/月报按钮直接扫描原始数据目录生成输出,无 foundation 查询、无 fail-closed;backend `report_service.py:105` 明确月报未迁移 foundation。
- Risk:数据口径绕过统一 foundation(清洗/校验/品牌归属全跳过),raw 文件结构变化直接破坏正式输出;违反 AGENTS.md Mandatory Data Path。
- Recommended direction:对齐美团模式(sync→ingest→fact_* 读取);raw read_table 仅保留 intake/迁移工具。
- Suggested TASK: **RPT-002**

### ISSUE-02 — app.py 上帝模块 6004 行(P2)

- Severity 说明:由 P1 调整为 P2——当前证据主要是超大模块/职责混合/维护成本,未证明直接数据泄露、数据破坏、重大生产安全事故或当前高概率业务故障;按当前真实风险原则降级。保留 Finding 本身,不删除。
- Evidence: `intranet_app/app.py` 6004 行;`handle_get`(436-568 约 30 分支)/`handle_post`(570-649 约 25 分支);约 60 个内联 f-string HTML 渲染函数占 55-58% 行数;超长函数 `_automation_runs_page`(3802-3961,159 行)等。
- observed behavior:路由、HTML 模板、控制器、编排、部分存储调用全部混合;无模板引擎、无分层。
- Risk:任何修改触碰面大、测试需要 mock 巨对象、交接困难;核心结构严重阻碍开发。
- Recommended direction:先抽公共渲染/控制器模块(读优先),逐步迁移到 backend 服务层(与 AGENTS/PROJECT_STATUS TECH_DEBT 方向一致),不一次性重构。
- Suggested TASK: **RPT-003**(分期)

### ISSUE-03 — 双配置系统并存且行为不一致(P1)
- Evidence: `backend/core/config.py:144-161` dotenv_values 读 `.env`;`intranet_app/config.py:40-48` 仅 os.environ.get 不读 `.env`;`app.py:1138` 用 AppConfig(不读 env)的 result_dir 塞 task payload。
- observed behavior:`.env` 中 `INTRANET_SECRET_KEY/ADMIN_PASSWORD` 对 `DEFAULT_CONFIG` 无效;同一仓库两套配置语义。
- Risk:配置失效静默发生(运维以为设置了密钥实际未生效),安全与部署行为不可预期。
- Recommended direction:统一配置加载(app 启动时用同一 dotenv 逻辑);secret key/admin password 缺失时 fail-closed。
- Suggested TASK: **RPT-004**

### ISSUE-04 — /scenario 上传 raw 直驱 P2 处理器(P2)
- Evidence: `app.py:585-588`(route `/scenario/*/run`)→ `app.py:965` `read_table(uploaded_file...)` → `app.py:969-970` `PROCESSORS[scenario_key](rows)` → save_job;PROCESSORS 含 `ai_selection.process`/`copy_content.process`(app.py:97-101)。
- observed behavior:用户上传原始 CSV/XLSX 直接驱动 P2 正式输出。
- Risk:违反 AGENTS.md:63;口径绕过 foundation;processors 为纯函数所以影响限于输入质量。
- Recommended direction:scenario 入口改走 foundation,或降级为诊断工具。
- Suggested TASK: RPT-002

### ISSUE-05 — 安踏黑名单上传 raw 直驱 P1 输出(P2)
- Evidence: `_handle_anta_blacklist_run`(`app.py:1492-1532`)要求上传 4 个 raw 文件直接生成 P1 黑名单输出。
- Recommended direction:同 ISSUE-04,改走 foundation。
- Suggested TASK: RPT-002

### ISSUE-06 — 默认密钥 fail open(P2)
- Evidence: `intranet_app/config.py:43` `INTRANET_SECRET_KEY` 默认 `"change-this-before-shared-intranet-use"`;`:48` `INTRANET_ADMIN_PASSWORD` 默认 `"admin123"`;LAN 模式只校验 admin 密码强度不校验 secret key 默认值。
- Risk:LAN/未来公网暴露时默认密钥可被利用。
- Recommended direction:非 localhost 模式下 secret key 必须显式配置,否则启动失败。
- Suggested TASK: RPT-004

### ISSUE-07 — backend 新层"真 wiring 假分层"+ 双套 DI 装配(P2)
- Evidence: `backend/repositories/sqlite/*` 为 AppStorage 转发器;`app.py:1208-1230` 与 `container.py:178-221` 双套装配同一对象图。
- Risk:抽象层无实际收益;两处装配易漂移。
- Recommended direction:收敛到 container 唯一装配源;或明确 repository 独立化后再保留接口。
- Suggested TASK: RPT-003

### ISSUE-08 — 内部异常字符串原样回传 UI/API 且无 traceback(P2)
- Evidence: 多处 handler 把 `str(exc)` 渲染进错误页/返回前端;无结构化错误码。
- Risk:路径/内部信息暴露;用户无法获得可操作的错误;审计留痕弱。
- Recommended direction:统一错误响应(code/message),内部日志带 traceback。
- Suggested TASK: **RPT-005**

### ISSUE-09 — 测试基线不可信(P2)
- Evidence: 隔离运行 265 tests:FAIL 5 + ERROR 1。3 个依赖 Git 未入库的规划排期 xlsx(`app.py:94/2495`);3 个 task-detail 断言与代码文案不同步(`tests/test_task_detail_diagnostics.py` 断言英文 "Result Asset"/"download available"、`tests/test_task_page.py` 断言"暂无可下载文件",页面为中文新文案)。
- Risk:无法建立可信回归基线;新改动无法判断是否引入回归。
- Recommended direction:测试数据改为 synthetic fixture;同步 task-detail 断言与文案;规划 xlsx 读取改为可选 fixture 或 mock。
- Suggested TASK: **RPT-006**

### ISSUE-10 — 本机绝对路径硬编码(P2, 文档部分 P3)
- Evidence: `intranet_app/anta_retail_launcher.py:10` `C:\Users\JM042403\Documents\安踏即时零售（上下架筛选+选品）`;`app.py:93` Desktop 路径;`app.py:2870` Downloads 路径;`tools/inspect_workbooks.mjs:3`、`tools/match_module_hours.mjs:8` `C:/Users/JM042403/Downloads/...`;`AGENTS.md:46`/`CONTRIBUTING.md:60`/`MASTER_PROMPT.md:424`/`README.md:46` 测试命令含 codex-runtimes 绝对路径且 `src` 目录不存在。
- Risk:其他开发机/CI/Docker 直接运行失败;违反 AGENTS.md 可迁移规范。
- Recommended direction:路径全部收敛到 settings/env;AGENTS/README 测试命令改为可移植形式。
- Suggested TASK: **RPT-007**

### ISSUE-11 — Public Repository Governance(P2)
- Evidence: Repository visibility=PUBLIC;业务中台代码无已证实泄露,但业务性质应私有。
- Recommended direction:转 Private(由 ChatGPT/用户批准);如转 Private,后续删除 GitHub Actions/分支保护审计另行 TASK。
- Suggested TASK: RPT-008(governance)

### ISSUE-12 — 死代码 _load_anta_meituan_sources 全家(含 Downloads fallback)(P3)

- Severity 说明:由 P2 统一为 P3——`_load_anta_meituan_sources` 及其 helper(`_daily_sources_with_lookback`/`_select_meituan_source`)含 raw/Downloads fallback,但当前审计确认**无生产调用者、unreachable、dead code**;当前风险是未来错误重新 wiring,而非当前正式业务路径正在绕过 foundation。
- Evidence: `app.py:1598-1636`(`_load_anta_meituan_sources`)、`1721-1743`(`_daily_sources_with_lookback`)、`1745-1782`(`_select_meituan_source`)全仓库无生产调用者;生产路径用 `_load_anta_meituan_sources_from_foundation`(app.py:1041)。
- Risk:一旦被重新接线即直接违反 AGENTS.md(Downloads/01_raw_data fallback);当前不可达故非数据泄露。
- Recommended direction:删除或标注 legacy 诊断工具并禁止重新接线。
- Suggested TASK: RPT-003

### ISSUE-13 — PostgreSQL skeleton / database 设计物 dead code(P3)
- Evidence: `database/postgresql/schema.sql` + README("design artifact only");`backend/repositories/postgresql/*` 写方法 `NotImplementedError`,仅测试引用;`container.py:143-144` 强制 sqlite;requirements.txt 无 psycopg2。
- Recommended direction:维持 skeleton 现状,迁移到实际 TASK 时再实现;不提前清理(避免误删设计)。
- Suggested TASK: 无需独立 TASK,并入 RPT-003 备注

### ISSUE-14 — dashboard 读桌面/下载真实 Excel(P3,非正式输出)
- Evidence: `app.py:93`(CHANNEL_BRAND_DISTRIBUTION_PATH 指向真实桌面路径)、`app.py:2870`(Downloads/内容任务耗时统计.xlsx);仅首页展示用,缺失返回空。
- Recommended direction:迁移至配置或 foundation;至少改为可配置。
- Suggested TASK: RPT-007

### ISSUE-15 — 重复代码(P3)
- Evidence: `_group_development_tree_panel` 同名两次(app.py:2006-2054 被 2205-2236 覆盖);multipart 解析近重复 3 次;`_format_efficiency_gain`/`_format_time_saved` 结构相同。
- Recommended direction:随 RPT-003 分期收敛。
- Suggested TASK: RPT-003

### ISSUE-16 — 配置 silent fallback / AI_PROVIDER 死配置(P3)
- Evidence: `REPORT_TASK_MODE` 非法值 warning+回退 legacy(backend/core/config.py:164-172;app.py:105-110);`AI_PROVIDER` 仅 bailian 分支实现(ai_service.py:71,102);`.env.example:16` SQLITE_PATH 为 Docker 路径。
- Recommended direction:非法值 fail-closed;移除死配置或实现分支检查。
- Suggested TASK: RPT-004

### ISSUE-17 — 文档编码损坏 / 文档量大(P3)
- Evidence: `PROJECT_KNOWLEDGE_BASE.md:4` 含乱码(旧工作区路径,编码损坏);46 个 .md 文档,PROJECT_STATUS/迁移文档有失去 Source of Truth 价值趋势。
- Recommended direction:修复编码;文档收敛以 GitHub/代码为 Source of Truth。
- Suggested TASK: RPT-009(文档治理)

### ISSUE-18 — 任务系统灰度与 automation 模块不相通(P3)
- Evidence: TaskSubmitter/TaskRunner 仅覆盖美团日报一景;`REPORT_TASK_MODE` 默认 legacy;automation 任务模块与任务系统互不相通。
- Recommended direction:明确灰度状态并记录;未来统一任务模型时再收敛。
- Suggested TASK: RPT-003(备注)

## 16. Follow-up TASK Proposals

> 仅提案,不创建;由 ChatGPT Review 后决定接受/合并/删除/调整优先级。

| TASK | 方向 | 关联 Issue | 建议优先级 |
|---|---|---|---|
| **RPT-002** | 数据边界合规:安踏周报/月报/scenario/黑名单改走 foundation | ISSUE-01/04/05 | **高 (HIGH)** |
| **RPT-003** | 架构收敛:app.py 分期拆分 + 单 DI 装配 + 死代码清理 | ISSUE-02/07/12/15/18 | 中(不提升;业务输出优先于架构清理) |
| **RPT-004** | 配置统一:单配置系统 + 密钥 fail-closed + 非法值 fail-closed | ISSUE-03/06/16 | **高 (HIGH)** |
| **RPT-005** | 异常/错误响应硬化 + traceback 审计日志 | ISSUE-08 | 中 |
| **RPT-006** | 测试基线修复:synthetic fixture + 断言同步 | ISSUE-09 | **高 (HIGH)** |
| **RPT-007** | 可移植性:本机绝对路径 → settings/env + 文档命令修复 | ISSUE-10/14 | 中 |
| **RPT-008** | Repository visibility governance(转 Private) | ISSUE-11 | 中(需 ChatGPT/用户决策) |
| **RPT-009** | 文档治理:编码修复 + 文档收敛 | ISSUE-17 | 低 |

## 17. Execution Log

时间标注说明:审计 Gate 的精确分钟未逐条落盘,写 `time unavailable`;commit/PR 时间以 git/GitHub 实际记录为准。

```
time unavailable | PRECHECK: worktree 不 clean(12 modified + 7 untracked)→ BLOCKED → Triage → Isolated Worktree 方案
time unavailable | AUDIT WORKTREE CREATED: C:\...\workspace_rpt001, branch chore/rpt-001-engineering-baseline, HEAD a25ef13, clean
time unavailable | 原工作区 FROZEN: modified=12, untracked=7(未变, 与 Worktree 创建前一致)
time unavailable | INVENTORY COMPLETE: 242 tracked files
time unavailable | SECURITY AUDIT COMPLETE: HEAD + history 无敏感数据; P0=none
time unavailable | DATA BOUNDARY AUDIT COMPLETE: 美团/P2 合规; 安踏周报月报/scenario/黑名单违规
time unavailable | ARCHITECTURE / CODE QUALITY / CONFIG / LOGGING / EXCEPTION AUDIT COMPLETE
time unavailable | TEST AUDIT COMPLETE: Ran 265 tests, PASS 259 / FAIL 5 / ERROR 1, 隔离安全
time unavailable | DOCUMENTATION / PORTABILITY AUDIT COMPLETE
time unavailable | REPORT COMPLETE (docs/RPT-001_ENGINEERING_BASELINE.md)
time unavailable | SELF REVIEW COMPLETE
<commit>      | COMMIT + PUSH + PR (docs(RPT-001): add reporting automation engineering baseline audit)
```

## 18. Tests Executed

```text
命令: python -m unittest discover -s tests -p "test_*.py"(隔离 Audit Worktree, PYTHONPATH=worktree 根)
结果: Ran 265 tests in 13.039s — FAILED (failures=5, errors=1)
PASS: 259
FAIL: test_dashboard_prioritizes_priority_entry... / test_page_and_dashboard_expose_automation_entry /
      test_failed_task_detail_shows_error_diagnostics / test_success_task_detail_shows_result_asset_status /
      test_task_detail_page_shows_status_and_error
ERROR: test_saved_not_improved_state_overrides_default_improved_rule
备注: 全部测试使用 tempfile/临时 DB/mock; 无外部网络、无真实业务数据访问(静态审计 + 运行双确认)
```

## 19. Tests Not Run

```text
无(项目标准 unittest 套件已在隔离环境完整执行 265 个用例)
备注: 原工作区未提交测试(test_admin_initialization.py / test_project_health.py)不属于 baseline, 按指令未使用、未运行
```

## 20. Limitations

1. **本审计基于 committed baseline `a25ef13`**,与 GitHub 远程 main 一致;原工作区存在 **FROZEN_LOCAL_WIP**(12 modified + 7 untracked),被有意排除在本审计之外,不构成 Current HEAD / Git history leakage 判断依据。
2. **2 个本地 untracked Meituan 诊断文档**(`docs/MEITUAN_EXPORT_PLUGIN_DIAGNOSTIC.md`、`docs/MEITUAN_PLUGIN_DIAGNOSTIC_RESULT.md`)未检查正文——可能包含业务诊断材料,且不属于 Git history;按指令不读取、不纳入 Git。
3. 未读取任何真实业务数据文件(`data/local`、`ai_report_config_materials` 下 raw/manual 目录、runtime、真实 xlsx/csv 内容);仅审核代码路径与 tracked 模板/样例的元数据。
4. 复杂度的量化以人工审阅 + 静态扫描为准,未引入 linter/复杂度工具(ruff/lizard 未配置)。
5. 未执行端到端运行服务验证(未启动 `python -m intranet_app.app`),页面行为以代码审阅 + 单元测试为准。
6. 浏览器扩展、tools 工具脚本仅做代表性抽查,未逐行审计(非生产核心路径)。
7. 测试的 6 个 non-passing(5 FAIL + 1 ERROR)未修复(AUDIT ONLY);失败根因已记录(3 环境依赖 + 3 断言不同步)。

---

*本报告仅记录问题,不实施修复;修复建议以后续独立 RPT TASK 形式推进,最终由 ChatGPT Review 裁决。*
